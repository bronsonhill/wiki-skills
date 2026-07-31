#!/usr/bin/env python3
"""Wiki lint — deterministic checks for orphans, dangling links, index drift,
and frontmatter, for the CMAS wiki (wiki/).

Usage:
    python3 lint.py [WIKI_DIR]

Defaults WIKI_DIR to ../../../wiki relative to this script. Exits 0 if clean,
1 if any issues found. Prints a markdown report to stdout suitable for piping into
wiki/lint-reports/<date>.md.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

PAGE_DIRS = ["sources", "concepts", "entities", "materials", "lint-reports"]
# Pages that contain template/placeholder wikilinks — skip them when scanning for dangling links.
META_LINK_SOURCES = {"log"}
# Lint reports are frozen snapshots — don't scan for dangling links and don't require inbound links.
FROZEN_SECTIONS = {"lint-reports"}
INDEX_SECTIONS = {"sources", "entities", "concepts", "materials"}


def find_wiki_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    here = Path(__file__).resolve().parent
    candidate = here.parent.parent.parent / "wiki"
    if candidate.is_dir():
        return candidate
    raise SystemExit("Could not locate wiki dir; pass it as an argument.")


def collect_pages(wiki: Path) -> dict[str, Path]:
    """Map page slug (relative to wiki, without .md) -> absolute path."""
    pages: dict[str, Path] = {}
    for d in PAGE_DIRS:
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


def link_targets(text: str) -> list[str]:
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(text)]


def basename(slug: str) -> str:
    return slug.split("/", 1)[1] if "/" in slug else slug


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
    wiki = find_wiki_dir(sys.argv[1] if len(sys.argv) > 1 else None)
    pages = collect_pages(wiki)

    inbound: dict[str, set[str]] = defaultdict(set)
    dangling: list[tuple[str, str]] = []
    frontmatter_issues: list[tuple[str, str]] = []

    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        section = slug.split("/", 1)[0] if "/" in slug else slug

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
            elif section == "materials":
                for req in ("title", "type", "tags", "date"):
                    if req not in fm:
                        frontmatter_issues.append((slug, f"material page missing `{req}`"))

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
    META = {"index", "log"}
    orphans = [
        s for s in pages
        if s not in META
        and pages[s].name != "index.md"
        and s.split("/", 1)[0] not in FROZEN_SECTIONS
        and not inbound[s]
    ]

    # Index drift: wiki pages not listed in their section's own index.md.
    index_drift: list[str] = []
    section_index_text: dict[str, str] = {}
    for section in INDEX_SECTIONS:
        idx = wiki / section / "index.md"
        section_index_text[section] = idx.read_text(encoding="utf-8") if idx.exists() else ""
    for slug in pages:
        if slug in META or pages[slug].name == "index.md":
            continue
        section = slug.split("/", 1)[0]
        if section not in INDEX_SECTIONS:
            continue
        if f"[[{basename(slug)}]]" not in section_index_text[section]:
            index_drift.append(slug)

    # Report
    issues = len(dangling) + len(orphans) + len(index_drift) + len(frontmatter_issues)
    print("# Wiki lint report\n")
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
        print(f"## Index drift — pages missing from their section `index.md` ({len(index_drift)})")
        for s in sorted(index_drift):
            print(f"- `{s}`")
        print()
    if frontmatter_issues:
        print(f"## Frontmatter issues ({len(frontmatter_issues)})")
        for slug, msg in sorted(frontmatter_issues):
            print(f"- `{slug}`: {msg}")
        print()
    if issues == 0:
        print("All checks passed.")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
