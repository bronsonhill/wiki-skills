#!/usr/bin/env python3
"""Convert an Obsidian Spaced Repetition cue-card deck into an Anki-importable TSV.

Usage:
    python3 to_anki_tsv.py <path-to>/<topic>-cue-cards.md

Writes `<deck>.anki.tsv` next to the input file: a `#separator:tab / #html:true /
#tags column:3` header followed by three tab-separated columns (Front, Back,
Tags), one row per card. Wikilinks are stripped to their display text and
answer newlines become `<br>` since Anki fields are HTML.

Anki import: File -> Import, pick the .tsv. The header lines tell Anki the
separator, that fields are HTML, and that column 3 is tags, so no manual
column mapping is needed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|([^\]]+))?\]\]")
TAG_RE = re.compile(r"#card/[\w-]+")
DECK_HEADER_RE = re.compile(r"^#flashcards/([\w-]+)", re.MULTILINE)


def strip_wikilinks(text: str) -> str:
    def repl(m: re.Match) -> str:
        return m.group(2) if m.group(2) else m.group(1)
    return WIKILINK_RE.sub(repl, text)


def to_html_field(text: str) -> str:
    text = strip_wikilinks(text.strip())
    text = TAG_RE.sub("", text).strip()
    return text.replace("\n", "<br>").replace("\t", " ")


TAG_LINE_RE = re.compile(r"^(?:#card/[\w-]+\s*)+$")


def parse_deck(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    deck_match = DECK_HEADER_RE.search(text)
    deck_name = deck_match.group(1) if deck_match else "deck"

    cards: list[tuple[str, str, str]] = []
    section = "card"
    blocks = re.split(r"\n(?=## )", text)
    for block in blocks:
        heading_match = re.match(r"## (.+)", block)
        if heading_match:
            section = heading_match.group(1).strip().lower().replace(" ", "-")
            block = block[heading_match.end():]
        if section == "deck-notes":
            continue

        lines = block.split("\n")
        qpositions = [i for i, line in enumerate(lines) if line.strip() == "?"]

        def question_start(qpos: int) -> int:
            # Contiguous run of non-blank lines immediately above the "?".
            start = qpos
            j = qpos - 1
            while j >= 0 and lines[j].strip():
                start = j
                j -= 1
            return start

        starts = [question_start(qpos) for qpos in qpositions]

        for idx, qpos in enumerate(qpositions):
            question = "\n".join(lines[starts[idx]:qpos]).strip()
            # Default answer end: right before the next question's own
            # non-blank run (used when no tag line separates them).
            next_start = starts[idx + 1] if idx + 1 < len(qpositions) else len(lines)
            search_end = qpositions[idx + 1] if idx + 1 < len(qpositions) else len(lines)
            tags = ""
            answer_end = next_start
            for k in range(qpos + 1, search_end):
                if TAG_LINE_RE.match(lines[k].strip()):
                    tags = " ".join(TAG_RE.findall(lines[k]))
                    answer_end = k
                    break
            answer = "\n".join(lines[qpos + 1:answer_end]).strip()
            if not tags:
                tags = f"card::{deck_name}"
            front = to_html_field(question)
            back = to_html_field(answer)
            if front and back:
                cards.append((front, back, tags))
    return deck_name, cards


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: to_anki_tsv.py <deck.md>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"ERROR: no such file: {src}", file=sys.stderr)
        return 1

    deck_name, cards = parse_deck(src.read_text(encoding="utf-8"))
    if not cards:
        print("WARNING: no cards parsed — check the deck follows the Q?\\n?\\nA format", file=sys.stderr)

    out_path = src.with_suffix("").with_suffix(".anki.tsv")
    with out_path.open("w", encoding="utf-8") as f:
        f.write("#separator:tab\n")
        f.write("#html:true\n")
        f.write("#tags column:3\n")
        for front, back, tags in cards:
            f.write(f"{front}\t{back}\t{tags}\n")

    print(f"OK: {out_path} ({len(cards)} cards)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
