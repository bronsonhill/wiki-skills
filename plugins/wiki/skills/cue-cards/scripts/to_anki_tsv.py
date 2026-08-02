#!/usr/bin/env python3
"""Convert an Obsidian Spaced Repetition cue-card deck into an Anki-importable TSV.

Usage:
    python3 to_anki_tsv.py <path-to>/<topic>-cue-cards.md

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
# the Obsidian SR plugin's inline review state — never part of the card
SR_RE = re.compile(r"^\s*<!--SR:.*-->\s*$")


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

        # One card per blank-line-separated block: the question, a lone "?",
        # then the answer. Splitting on "?" alone cannot find the end of an
        # answer, and runs each card into the question that follows it.
        for card_block in re.split(r"\n\s*\n", block):
            lines = card_block.strip("\n").split("\n")
            try:
                sep = next(i for i, l in enumerate(lines) if l.strip() == "?")
            except StopIteration:
                continue
            if sep == 0 or sep == len(lines) - 1:
                continue

            question = "\n".join(lines[:sep]).strip()
            answer_lines = [l for l in lines[sep + 1:] if not SR_RE.match(l)]
            answer = "\n".join(answer_lines).strip()
            if not question or not answer:
                continue

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
