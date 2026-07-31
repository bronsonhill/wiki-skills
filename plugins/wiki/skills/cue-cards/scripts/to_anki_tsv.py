#!/usr/bin/env python3
"""Convert an Obsidian Spaced Repetition cue-card deck into an Anki-importable TSV.

Usage:
    python3 to_anki_tsv.py wiki/materials/<topic>-cue-cards.md

Writes `<deck>.anki.tsv` next to the input file: three tab-separated columns
(Front, Back, Tags), one row per card. Wikilinks are stripped to their display
text and answer newlines become `<br>` since Anki fields are HTML.

Anki import: File -> Import, pick the .tsv, set field separator to Tab, map
columns to Front / Back / Tags.
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

        # Cards are separated by a lone "?" line.
        parts = re.split(r"\n\?\n", block)
        for i in range(len(parts) - 1):
            question = parts[i].strip()
            # Drop any leading blank lines / stray heading remnants.
            question = question.lstrip("\n").strip()
            if not question:
                continue
            answer_block = parts[i + 1]
            # Answer runs until the next question would start (blank line then
            # non-empty line without a following lone "?") — simplest robust rule:
            # take the answer up to the next blank-line-separated paragraph break
            # if a tag line signals the end, otherwise the whole remainder up to
            # the next question boundary (already split by parts).
            answer = answer_block.strip()
            tags_found = TAG_RE.findall(answer)
            tags = " ".join(tags_found) if tags_found else f"card::{deck_name}"
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
        for front, back, tags in cards:
            f.write(f"{front}\t{back}\t{tags}\n")

    print(f"OK: {out_path} ({len(cards)} cards)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
