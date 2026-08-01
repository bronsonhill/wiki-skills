#!/usr/bin/env python3
"""Wiki lint — deterministic checks for orphans, dangling links, index drift,
frontmatter, and domain hygiene.

Usage:
    python3 lint.py [WIKI_DIR]

Configuration comes from `.claude/wiki-schema.md` in the repo containing the wiki
(see CONFIG_DEFAULTS). With no argument the wiki is located by walking up from the
current working directory looking for a `.claude/wiki-schema.md`, then falling back
to `./wiki`. Exits 0 if clean, 1 if any issues found. Prints a markdown report to
stdout suitable for piping into <wiki>/lint-reports/<date>.md.
"""

from __future__ import annotations

import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

CONFIG_DEFAULTS = {
    "wiki_root": "wiki",
    "derived_dir": "materials",
    "index_style": "per-section",
    "domains": [],
}

# Pages that contain template/placeholder wikilinks — skip them when scanning for dangling links.
META_LINK_SOURCES = {"log"}
# Lint reports are frozen snapshots — don't scan for dangling links and don't require inbound links.
FROZEN_SECTIONS = {"lint-reports"}
META = {"index", "log"}


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def parse_list(raw: str) -> list[str]:
    """Parse a YAML inline list or bare scalar into a list of strings."""
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [v.strip().strip("\"'") for v in raw.split(",") if v.strip()]


def find_schema(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        candidate = d / ".claude" / "wiki-schema.md"
        if candidate.is_file():
            return candidate
    return None


def load_config(start: Path) -> tuple[dict, Path | None]:
    cfg = dict(CONFIG_DEFAULTS)
    schema = find_schema(start)
    if schema:
        fm = parse_frontmatter(schema.read_text(encoding="utf-8"))
        for key in CONFIG_DEFAULTS:
            if key in fm:
                cfg[key] = parse_list(fm[key]) if key == "domains" else fm[key]
    return cfg, schema


def find_wiki_dir(arg: str | None, cfg: dict, schema: Path | None) -> Path:
    if arg:
        return Path(arg).resolve()
    base = schema.parent.parent if schema else Path.cwd()
    candidate = (base / cfg["wiki_root"]).resolve()
    if candidate.is_dir():
        return candidate
    raise SystemExit(
        f"Could not locate wiki dir (looked for {candidate}); pass it as an argument."
    )


def collect_pages(wiki: Path, page_dirs: list[str]) -> dict[str, Path]:
    """Map page slug (relative to wiki, without .md) -> absolute path."""
    pages: dict[str, Path] = {}
    for d in page_dirs:
        sub = wiki / d
        if not sub.is_dir():
            continue
        for md in sub.rglob("*.md"):
            if "assets" in md.parts:
                continue
            rel = md.relative_to(wiki).with_suffix("")
            pages[str(rel)] = md
    for root_page in ("index", "log"):
        p = wiki / f"{root_page}.md"
        if p.exists():
            pages[root_page] = p
    return pages


def link_targets(text: str) -> list[str]:
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(text)]


def basename(slug: str) -> str:
    return slug.split("/", 1)[1] if "/" in slug else slug


def section_of(slug: str) -> str:
    return slug.split("/", 1)[0] if "/" in slug else slug


def domain_values(fm: dict[str, str]) -> list[str]:
    """Return domain labels from frontmatter (string or [a, b] array form)."""
    return parse_list(fm.get("domain", ""))


def resolve(target: str, pages: dict[str, Path]) -> str | None:
    """Resolve a wikilink target to a page slug, or None if dangling.

    Wikilinks are written as bare filenames (e.g. `[[cellular-automaton]]`), matching
    Obsidian/Quartz shorthand resolution — so match on exact slug first, then on the
    basename of any page regardless of its section.
    """
    if target in pages:
        return target
    if "/" not in target:
        for slug in pages:
            if basename(slug) == target:
                return slug
    return None


def main() -> int:
    cfg, schema = load_config(Path.cwd())
    wiki = find_wiki_dir(sys.argv[1] if len(sys.argv) > 1 else None, cfg, schema)

    derived = cfg["derived_dir"]
    index_sections = {"sources", "entities", "concepts", derived}
    page_dirs = [*index_sections, "lint-reports"]
    allowed_domains = set(cfg["domains"])
    check_domains = bool(allowed_domains)

    pages = collect_pages(wiki, sorted(page_dirs))

    inbound: dict[str, set[str]] = defaultdict(set)
    dangling: list[tuple[str, str]] = []
    frontmatter_issues: list[tuple[str, str]] = []
    domain_issues: list[tuple[str, str]] = []
    page_domains: dict[str, list[str]] = {}

    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        section = section_of(slug)

        # Frontmatter schema check (skip section index.md pages and cue-card decks).
        is_index_page = path.name == "index.md"
        is_cue_card_deck = text.lstrip().startswith("#flashcards/")
        if not is_index_page and not is_cue_card_deck:
            if section == "concepts" and fm.get("type") != "concept":
                frontmatter_issues.append((slug, "concept page missing `type: concept`"))
            elif section == "entities" and fm.get("type") != "entity":
                frontmatter_issues.append((slug, "entity page missing `type: entity`"))
            elif section == "sources":
                if fm.get("type") != "source":
                    frontmatter_issues.append((slug, "source page missing `type: source`"))
                if "link" not in fm:
                    frontmatter_issues.append((slug, "source page missing `link` field"))
            elif section == derived:
                for req in ("title", "type", "tags", "date"):
                    if req not in fm:
                        frontmatter_issues.append((slug, f"{derived} page missing `{req}`"))

            if check_domains and section in index_sections:
                doms = domain_values(fm)
                page_domains[slug] = doms
                if not doms:
                    domain_issues.append((slug, "missing `domain` field"))
                for d in doms:
                    top = d.split("/", 1)[0]
                    if top not in allowed_domains:
                        domain_issues.append(
                            (slug, f"unknown top-level domain `{top}` in `{d}`")
                        )

        scan_dangling = slug not in META_LINK_SOURCES and section not in FROZEN_SECTIONS
        for tgt in link_targets(text):
            resolved = resolve(tgt, pages)
            if resolved is None:
                if not scan_dangling:
                    continue
                if tgt.endswith((".pdf", ".png", ".jpg", ".txt")):
                    continue
                dangling.append((slug, tgt))
            else:
                inbound[resolved].add(slug)

    # Orphans: pages with no inbound links (excluding meta, index pages themselves).
    orphans = [
        s for s in pages
        if s not in META
        and pages[s].name != "index.md"
        and section_of(s) not in FROZEN_SECTIONS
        and not inbound[s]
    ]

    # Index drift: pages not listed in the index that is meant to catalog them.
    index_drift: list[str] = []
    root_index_text = ""
    root_index = wiki / "index.md"
    if root_index.exists():
        root_index_text = root_index.read_text(encoding="utf-8")
    section_index_text: dict[str, str] = {}
    for section in index_sections:
        idx = wiki / section / "index.md"
        section_index_text[section] = idx.read_text(encoding="utf-8") if idx.exists() else ""
    for slug in pages:
        if slug in META or pages[slug].name == "index.md":
            continue
        section = section_of(slug)
        if section not in index_sections:
            continue
        haystack = (
            section_index_text[section]
            if cfg["index_style"] == "per-section"
            else root_index_text
        )
        if f"[[{basename(slug)}]]" not in haystack:
            index_drift.append(slug)

    # Name collisions: near-duplicate filenames in the same section whose domains
    # don't overlap — decide consciously whether to merge or rename.
    collisions: list[tuple[str, str]] = []
    if check_domains:
        by_section: dict[str, list[str]] = defaultdict(list)
        for slug in page_domains:
            by_section[section_of(slug)].append(slug)
        for section, slugs in by_section.items():
            for i, si in enumerate(sorted(slugs)):
                for sj in sorted(slugs)[i + 1:]:
                    ratio = difflib.SequenceMatcher(
                        None, basename(si), basename(sj)
                    ).ratio()
                    if ratio < 0.85:
                        continue
                    if set(page_domains[si]) & set(page_domains[sj]):
                        continue
                    collisions.append((si, sj))

    # Report
    issues = (len(dangling) + len(orphans) + len(index_drift)
              + len(frontmatter_issues) + len(domain_issues) + len(collisions))
    print("# Wiki lint report\n")
    print(f"- Wiki: `{wiki}`")
    print(f"- Schema: `{schema}`" if schema else "- Schema: *(not found — using defaults)*")
    print(f"- Pages scanned: {len(pages)}")
    print(f"- Issues found: **{issues}**\n")

    if dangling:
        print(f"## Dangling links ({len(dangling)})")
        for src, tgt in sorted(set(dangling)):
            print(f"- `{src}` → `[[{tgt}]]`")
        print()
    if orphans:
        print(f"## Orphan pages ({len(orphans)})")
        for s in sorted(orphans):
            print(f"- `{s}`")
        print()
    if index_drift:
        label = "their section `index.md`" if cfg["index_style"] == "per-section" else "`index.md`"
        print(f"## Index drift — pages missing from {label} ({len(index_drift)})")
        for s in sorted(index_drift):
            print(f"- `{s}`")
        print()
    if frontmatter_issues:
        print(f"## Frontmatter issues ({len(frontmatter_issues)})")
        for slug, msg in sorted(frontmatter_issues):
            print(f"- `{slug}`: {msg}")
        print()
    if domain_issues:
        print(f"## Domain issues ({len(domain_issues)})")
        for slug, msg in sorted(domain_issues):
            print(f"- `{slug}`: {msg}")
        print()
    if collisions:
        print(f"## Possible name collisions across domains ({len(collisions)})")
        for si, sj in sorted(set(collisions)):
            print(f"- `{si}` ↔ `{sj}`")
        print()
    if issues == 0:
        print("All checks passed.")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
