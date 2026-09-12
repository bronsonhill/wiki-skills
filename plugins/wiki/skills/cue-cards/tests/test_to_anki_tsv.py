import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "to_anki_tsv.py"
spec = importlib.util.spec_from_file_location("to_anki_tsv", SCRIPT_PATH)
to_anki_tsv = importlib.util.module_from_spec(spec)
sys.modules["to_anki_tsv"] = to_anki_tsv
spec.loader.exec_module(to_anki_tsv)

parse_deck = to_anki_tsv.parse_deck


THREE_CARD_DECK = """#flashcards/test-deck

## Elaborative Interrogation

Question one?
?
Answer one.
#card/test #card/one

Question two?
?
Answer two.
#card/test #card/two

Question three?
?
Answer three.
#card/test #card/three
"""


def test_three_card_section_round_trips_without_bleed():
    _, cards = parse_deck(THREE_CARD_DECK)
    assert len(cards) == 3
    fronts = [c[0] for c in cards]
    backs = [c[1] for c in cards]
    assert fronts == ["Question one?", "Question two?", "Question three?"]
    assert backs == ["Answer one.", "Answer two.", "Answer three."]
    for front, back in zip(fronts, backs):
        for other_front in fronts:
            if other_front != front:
                assert other_front not in back
        for other_back in backs:
            if other_back != back:
                assert other_back not in front


MULTI_LINE_ANSWER_DECK = """#flashcards/test-deck

## Elaborative Interrogation

What are the steps?
?
The steps are:

1. First step, with detail.
2. Second step, with detail.

There is also a blank-line-separated closing remark.
#card/test #card/steps
"""


def test_answer_with_blank_lines_and_numbered_list_kept_whole():
    _, cards = parse_deck(MULTI_LINE_ANSWER_DECK)
    assert len(cards) == 1
    front, back, tags = cards[0]
    assert front == "What are the steps?"
    assert "First step, with detail." in back
    assert "Second step, with detail." in back
    assert "closing remark" in back
    assert tags == "#card/test #card/steps"


NO_TAG_LINE_DECK = """#flashcards/untagged-deck

## Elaborative Interrogation

Question without a tag line?
?
Answer without a tag line.

Question two?
?
Answer two.
#card/test
"""


def test_card_without_tag_line_falls_back_to_card_deck_name():
    deck_name, cards = parse_deck(NO_TAG_LINE_DECK)
    assert len(cards) == 2
    assert cards[0][2] == f"card::{deck_name}"
    assert cards[1][2] == "#card/test"


DECK_NOTES_DECK = """#flashcards/test-deck

## Deck notes

This section holds authoring notes, not cards.

Not a real question?
?
Not a real answer.
#card/test

## Elaborative Interrogation

Real question?
?
Real answer.
#card/test
"""


def test_deck_notes_section_contributes_no_rows():
    _, cards = parse_deck(DECK_NOTES_DECK)
    assert len(cards) == 1
    assert cards[0][0] == "Real question?"
    assert cards[0][1] == "Real answer."


WIKILINK_DECK = """#flashcards/test-deck

## Elaborative Interrogation

What does [[some-target]] refer to?
?
It refers to [[some-target|a nicer label]] and to [[other-target#heading|another label]].
#card/test
"""


def test_wikilinks_stripped_to_display_text():
    _, cards = parse_deck(WIKILINK_DECK)
    assert len(cards) == 1
    front, back, _ = cards[0]
    assert front == "What does some-target refer to?"
    assert back == "It refers to a nicer label and to another label."


def test_output_file_starts_with_header_lines(tmp_path):
    deck_path = tmp_path / "week-99-cue-cards.md"
    deck_path.write_text(THREE_CARD_DECK, encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(deck_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    out_path = tmp_path / "week-99-cue-cards.anki.tsv"
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#separator:tab"
    assert lines[1] == "#html:true"
    assert lines[2] == "#tags column:3"


REGRESSION_DECK = """#flashcards/week-02

## Elaborative Interrogation

Q1?
?
A1.
#card/cmas #card/week-02

Q2?
?
A2.
#card/cmas #card/week-02

Q3?
?
A3.
#card/cmas #card/week-02
"""


def test_regression_no_bleed_signature_and_row_count_matches_separators():
    deck_name, cards = parse_deck(REGRESSION_DECK)
    question_mark_separators = REGRESSION_DECK.count("\n?\n")
    assert len(cards) == question_mark_separators
    for front, back, _ in cards:
        assert "<br> <br><br>" not in front
        assert "<br> <br><br>" not in back
