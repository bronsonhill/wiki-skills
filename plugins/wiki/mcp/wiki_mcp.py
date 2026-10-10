#!/usr/bin/env python3
"""Read-only MCP server over one or more wikis built with the wiki plugin.

Lets an agent session in any directory query a wiki that lives in another repo.
Speaks MCP's stdio transport (newline-delimited JSON-RPC 2.0) with the standard
library only, so it needs no install step. The plugin's `.mcp.json` starts it in
every session where the plugin is enabled.

Which wikis it serves comes from two registries, re-read on every tool call so a
newly added wiki works without restarting the session:

    ~/.config/wiki-skills/wikis.json     every session (WIKI_MCP_REGISTRY overrides)
    <project>/.claude/wikis.json         sessions in that project; wins on a name clash

Both map a name to a path: {"wikis": {"cmas": "~/Repositories/cmas"}}. The path is
either the consuming repo (its `.claude/wiki-schema.md` gives `wiki_root`) or the
wiki directory itself. Tools take the name as their `wiki` argument, which may be
omitted when only one wiki is registered.

Usage:
    wiki_mcp.py [--wiki NAME=PATH ...]          serve (extra wikis on top of the registries)
    wiki_mcp.py add NAME PATH [--project DIR]   register a wiki
    wiki_mcp.py remove NAME [--project DIR]     unregister a wiki
    wiki_mcp.py list [--project DIR]            show what a session in DIR would see
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SERVER_NAME = "wiki"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL = "2025-06-18"

WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
TOKEN_RE = re.compile(r"[a-z0-9]+")

USER_REGISTRY = Path("~/.config/wiki-skills/wikis.json")
PROJECT_REGISTRY = Path(".claude/wikis.json")

# Lint reports are frozen snapshots of other pages' problems; they add noise to search.
SKIP_DIRS = {"lint-reports", ".obsidian", ".git"}

INSTRUCTIONS = """\
Read-only access to personal wikis built with the wiki plugin (Karpathy pattern).
Pages are markdown with YAML frontmatter (title, type, tags, optional domain) and
link to each other with [[wikilinks]]; a link's target is a page id you can pass to
wiki_read. Start with wiki_index to see the catalog, use wiki_search when the index
doesn't point at the answer, then wiki_read candidate pages in full. Answer from the
pages and cite the page ids you used, e.g. (concepts/agent-based-model). Say so when
the wiki has no page covering the question rather than filling the gap from memory."""


# --- wiki loading -----------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("\"'")
    return fm, text[m.end():]


def parse_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [v.strip().strip("\"'") for v in raw.split(",") if v.strip()]


def resolve_wiki_root(path: Path) -> Path:
    """Map a consuming-repo path (or a wiki dir) to the wiki root directory."""
    path = path.expanduser().resolve()
    for d in [path, *path.parents]:
        schema = d / ".claude" / "wiki-schema.md"
        if schema.is_file():
            fm, _ = parse_frontmatter(schema.read_text(encoding="utf-8"))
            return (d / fm.get("wiki_root", "wiki")).resolve()
    return path


class Page:
    __slots__ = ("id", "path", "meta", "body", "links")

    def __init__(self, page_id: str, path: Path, meta: dict[str, str], body: str):
        self.id = page_id
        self.path = path
        self.meta = meta
        self.body = body
        self.links = {link.strip().removesuffix(".md") for link in WIKILINK_RE.findall(body)}

    @property
    def title(self) -> str:
        return self.meta.get("title") or self.id.rsplit("/", 1)[-1]


class Wiki:
    def __init__(self, name: str, root: Path):
        self.name = name
        self.root = root

    def pages(self) -> list[Page]:
        # Re-read on every call: wikis are small and get edited while sessions run.
        out = []
        for path in sorted(self.root.rglob("*.md")):
            rel = path.relative_to(self.root)
            if SKIP_DIRS.intersection(rel.parts[:-1]):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            meta, body = parse_frontmatter(text)
            out.append(Page(rel.with_suffix("").as_posix(), path, meta, body))
        return out

    def resolve(self, ref: str, pages: list[Page]) -> Page | list[Page] | None:
        """Find a page by id, file path, wikilink, or bare stem.

        Returns the page, a list of candidates when a bare stem is ambiguous, or None.
        """
        ref = ref.strip()
        m = WIKILINK_RE.fullmatch(ref)
        if m:
            ref = m.group(1)
        ref = ref.strip().strip("/").removesuffix(".md")
        by_id = {p.id: p for p in pages}
        if ref in by_id:
            return by_id[ref]
        # Obsidian resolves [[name]] by filename anywhere in the vault.
        stem = ref.rsplit("/", 1)[-1]
        matches = [p for p in pages if p.id.rsplit("/", 1)[-1] == stem]
        if len(matches) == 1:
            return matches[0]
        # A section name means its index page.
        if f"{ref}/index" in by_id:
            return by_id[f"{ref}/index"]
        return matches or None


# --- tools ------------------------------------------------------------------


class ToolError(Exception):
    pass


def snippet(body: str, terms: list[str], width: int = 240) -> str:
    low = body.lower()
    hits = [i for t in terms if (i := low.find(t)) >= 0]
    start = max(0, min(hits) - width // 3) if hits else 0
    text = " ".join(body[start:start + width].split())
    return ("…" if start else "") + text + ("…" if start + width < len(body) else "")


def score(page: Page, terms: list[str]) -> int:
    title = page.title.lower()
    stem = page.id.rsplit("/", 1)[-1].replace("-", " ")
    phrase = " ".join(terms)
    tags = " ".join(parse_list(page.meta.get("tags", ""))).lower()
    body_tokens = TOKEN_RE.findall(page.body.lower())
    total = 0
    for t in terms:
        hits = sum(1 for tok in body_tokens if tok.startswith(t))
        if not hits and t not in title and t not in stem and t not in tags:
            return 0  # every term must appear somewhere
        total += 10 * (t in title or t in stem) + 5 * (t in tags) + min(hits, 10)
    # The page *about* the query (concepts/emergence for "emergence") beats long
    # digests that mention it on every line.
    if phrase in (" ".join(TOKEN_RE.findall(title)), stem):
        total += 100
    return total


class Server:
    def __init__(self, extra: dict[str, Wiki] | None = None, project_dir: Path | None = None,
                 use_registries: bool = True):
        self.extra = extra or {}
        self.project_dir = project_dir
        self.use_registries = use_registries

    @property
    def wikis(self) -> dict[str, Wiki]:
        found = load_registered(self.project_dir) if self.use_registries else {}
        return {**found, **self.extra}

    def wiki(self, args: dict) -> Wiki:
        wikis, name = self.wikis, args.get("wiki")
        if not wikis:
            raise ToolError("No wikis are registered. Ask the user to run /wiki:connect.")
        if name:
            if name not in wikis:
                raise ToolError(f"unknown wiki {name!r}; registered: {', '.join(wikis)}")
            wiki = wikis[name]
        elif len(wikis) == 1:
            wiki = next(iter(wikis.values()))
        else:
            raise ToolError(f"several wikis registered, pass `wiki`: {', '.join(wikis)}")
        if not wiki.root.is_dir():
            raise ToolError(f"wiki {wiki.name!r} is registered at {wiki.root}, which no longer exists")
        return wiki

    def tool_specs(self) -> list[dict]:
        wiki_prop = {
            "type": "string",
            "description": "Which wiki to use, by registered name. Optional when only one is registered.",
        }
        registered = ", ".join(f"{n} ({w.root})" for n, w in self.wikis.items()) or "none yet"
        return [
            {
                "name": "wiki_index",
                "description": (
                    "Return a wiki's catalog page. With no section, the root index.md; "
                    "with a section such as 'concepts', that section's index.md. "
                    f"Registered wikis: {registered}."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "wiki": wiki_prop,
                        "section": {"type": "string", "description": "e.g. concepts, entities, sources, materials"},
                    },
                },
            },
            {
                "name": "wiki_search",
                "description": (
                    "Keyword search over page titles, filenames, tags and bodies. Every "
                    "term must match; title and tag hits rank highest. Returns page ids "
                    "with a snippet. Use it when the index doesn't lead to the answer."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "wiki": wiki_prop,
                        "query": {"type": "string"},
                        "type": {"type": "string", "description": "Filter on frontmatter type: concept, entity, source, material"},
                        "domain": {"type": "string", "description": "Filter on frontmatter domain prefix, e.g. academic/nlp"},
                        "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "wiki_read",
                "description": (
                    "Read one page in full, with its frontmatter. Accepts a page id "
                    "(concepts/agent-based-model), a bare name, a [[wikilink]], or a "
                    "section name for its index. Also lists the pages that link to it."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"wiki": wiki_prop, "page": {"type": "string"}},
                    "required": ["page"],
                },
            },
        ]

    def call(self, name: str, args: dict) -> str:
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            raise ToolError(f"unknown tool {name!r}")
        return handler(args)

    def _wiki_index(self, args: dict) -> str:
        wiki = self.wiki(args)
        section = (args.get("section") or "").strip("/")
        path = wiki.root / section / "index.md" if section else wiki.root / "index.md"
        if not path.resolve().is_relative_to(wiki.root) or not path.is_file():
            sections = sorted(p.parent.name for p in wiki.root.glob("*/index.md"))
            raise ToolError(f"no index at {section or '/'}; sections with an index: {', '.join(sections)}")
        return path.read_text(encoding="utf-8")

    def _wiki_search(self, args: dict) -> str:
        wiki = self.wiki(args)
        terms = TOKEN_RE.findall(args.get("query", "").lower())
        if not terms:
            raise ToolError("query has no searchable words")
        limit = max(1, min(int(args.get("limit") or 10), 50))
        want_type, want_domain = args.get("type"), args.get("domain")
        ranked = []
        for page in wiki.pages():
            # The log and the indexes mention everything; wiki_index serves the latter.
            if page.id in ("log", "index") or page.id.endswith("/index"):
                continue
            if want_type and page.meta.get("type") != want_type:
                continue
            if want_domain and not any(d.startswith(want_domain) for d in parse_list(page.meta.get("domain", ""))):
                continue
            if s := score(page, terms):
                ranked.append((s, page))
        ranked.sort(key=lambda sp: (-sp[0], sp[1].id))
        if not ranked:
            return f"No pages match {args['query']!r} in {wiki.name}."
        lines = [f"{len(ranked)} match(es) in {wiki.name}; top {min(limit, len(ranked))}:", ""]
        for s, page in ranked[:limit]:
            kind = page.meta.get("type", "?")
            lines.append(f"- {page.id} — {page.title} [{kind}]")
            lines.append(f"  {snippet(page.body, terms)}")
        return "\n".join(lines)

    def _wiki_read(self, args: dict) -> str:
        wiki = self.wiki(args)
        pages = wiki.pages()
        found = wiki.resolve(args.get("page", ""), pages)
        if found is None:
            raise ToolError(f"no page {args.get('page')!r} in {wiki.name}; try wiki_search")
        if isinstance(found, list):
            raise ToolError("ambiguous name; candidates: " + ", ".join(p.id for p in found))
        stem = found.id.rsplit("/", 1)[-1]
        backlinks = sorted(
            p.id for p in pages
            if p is not found and (found.id in p.links or stem in p.links)
        )
        text = found.path.read_text(encoding="utf-8", errors="replace")
        footer = "\n\n---\nLinked from: " + (", ".join(backlinks) if backlinks else "(no pages)")
        return f"page id: {found.id}\n\n{text}{footer}"


# --- JSON-RPC over stdio ----------------------------------------------------


def handle(server: Server, msg: dict) -> dict | None:
    method, msg_id = msg.get("method"), msg.get("id")
    if msg_id is None:
        return None  # notification, e.g. notifications/initialized
    params = msg.get("params") or {}
    try:
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion", DEFAULT_PROTOCOL),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": server.tool_specs()}
        elif method == "tools/call":
            try:
                text = server.call(params.get("name", ""), params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": text}], "isError": False}
            except ToolError as e:
                result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"method not found: {method}"}}
    except Exception as e:  # keep serving after a bug in one request
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": repr(e)}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(server: Server, stdin=sys.stdin, stdout=sys.stdout) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
        else:
            reply = handle(server, msg)
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


# --- registries -------------------------------------------------------------


def user_registry() -> Path:
    return Path(os.environ.get("WIKI_MCP_REGISTRY") or USER_REGISTRY).expanduser()


def find_project_registry(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / PROJECT_REGISTRY).is_file():
            return d / PROJECT_REGISTRY
    return None


def read_registry(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"wiki_mcp: ignoring unreadable registry {path}: {e}", file=sys.stderr)
        return {}
    wikis = data.get("wikis") if isinstance(data, dict) else None
    return {str(k): str(v) for k, v in wikis.items()} if isinstance(wikis, dict) else {}


def write_registry(path: Path, entries: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"wikis": dict(sorted(entries.items()))}, indent=2) + "\n", encoding="utf-8")


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def load_registered(start: Path | None = None) -> dict[str, Wiki]:
    entries = read_registry(user_registry())
    entries.update(read_registry(find_project_registry((start or project_dir()).resolve())))
    return {name: Wiki(name, resolve_wiki_root(Path(path))) for name, path in entries.items()}


def tilde(path: Path) -> str:
    """Store paths under $HOME as ~/... so a project registry survives a username change."""
    home = Path.home()
    return "~/" + path.relative_to(home).as_posix() if path.is_relative_to(home) else str(path)


def cmd_add(name: str, path: str, project: str | None) -> int:
    repo = Path(path).expanduser().resolve()
    root = resolve_wiki_root(repo)
    if not (root / "index.md").is_file():
        print(f"error: no index.md at {root}; is {repo} a wiki built with the wiki plugin?", file=sys.stderr)
        return 1
    reg = Path(project).expanduser().resolve() / PROJECT_REGISTRY if project else user_registry()
    entries = read_registry(reg)
    old = entries.get(name)
    entries[name] = tilde(repo)
    write_registry(reg, entries)
    pages = sum(1 for _ in root.rglob("*.md"))
    verb = "updated" if old else "added"
    print(f"{verb} {name} -> {root} ({pages} pages) in {reg}")
    return 0


def cmd_remove(name: str, project: str | None) -> int:
    reg = Path(project).expanduser().resolve() / PROJECT_REGISTRY if project else user_registry()
    entries = read_registry(reg)
    if entries.pop(name, None) is None:
        print(f"error: {name!r} is not in {reg}", file=sys.stderr)
        return 1
    write_registry(reg, entries)
    print(f"removed {name} from {reg}")
    return 0


def cmd_list(project: str | None) -> int:
    start = Path(project).expanduser().resolve() if project else project_dir()
    proj = find_project_registry(start)
    print(f"user registry:    {user_registry()}")
    print(f"project registry: {proj or '(none above ' + str(start) + ')'}")
    wikis = load_registered(start)
    if not wikis:
        print("no wikis registered")
    for name, wiki in wikis.items():
        state = "ok" if (wiki.root / "index.md").is_file() else "MISSING"
        print(f"  {name}: {wiki.root} [{state}]")
    return 0


def parse_wikis(specs: list[str]) -> dict[str, Wiki]:
    wikis = {}
    for spec in specs:
        name, sep, path = spec.partition("=")
        if not sep:  # bare path: name it after the directory
            name, path = Path(spec).expanduser().resolve().name, spec
        wikis[name] = Wiki(name, resolve_wiki_root(Path(path)))
    return wikis


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    fmt = argparse.RawDescriptionHelpFormatter
    if argv and argv[0] in ("add", "remove", "list"):
        ap = argparse.ArgumentParser(prog="wiki_mcp.py", description=__doc__, formatter_class=fmt)
        sub = ap.add_subparsers(dest="cmd", required=True)
        add = sub.add_parser("add", help="register a wiki")
        add.add_argument("name")
        add.add_argument("path", help="consuming repo or wiki directory")
        rm = sub.add_parser("remove", help="unregister a wiki")
        rm.add_argument("name")
        sub.add_parser("list", help="show registered wikis")
        for p in (add, rm, sub.choices["list"]):
            p.add_argument("--project", metavar="DIR",
                           help="use DIR/.claude/wikis.json instead of the user registry")
        args = ap.parse_args(argv)
        if args.cmd == "add":
            return cmd_add(args.name, args.path, args.project)
        if args.cmd == "remove":
            return cmd_remove(args.name, args.project)
        return cmd_list(args.project)

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=fmt)
    ap.add_argument("--wiki", action="append", default=[], metavar="NAME=PATH",
                    help="serve this wiki on top of the registries; repeat for several")
    args = ap.parse_args(argv)
    serve(Server(parse_wikis(args.wiki)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
