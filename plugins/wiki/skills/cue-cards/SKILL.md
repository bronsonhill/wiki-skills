---
name: cue-cards
description: >
  Generate spaced-repetition cue cards from a personal wiki page (source, concept,
  entity or derived material). Cards test reasoning (why something holds, how a
  mechanism runs, how two ideas differ, what breaks) in preference to bare definitions.
  They are written once in Obsidian Spaced Repetition format and exported to an
  Anki-importable TSV, so they work in either tool. Use when the user says "make cue
  cards", "generate flashcards", "quiz me on", "revision cards for", "export to anki",
  "turn this page into cards", or otherwise wants flashcards from wiki content.
---

# Cue Card Generator

Writes cue cards from wiki pages for long-term retention. You write the card content
once, as an Obsidian Spaced Repetition deck (native `.md` in the wiki, wikilinks kept).
That deck is the source of truth, and a script converts it to an Anki import (`.tsv`,
wikilinks stripped because Anki has no equivalent).

Paths come from the consuming repo's `.claude/wiki-schema.md` (the configuration table
is in `ingest`). This skill reads `wiki_root`, `derived_dir`, `domains` and `subject`.

## Step 1: Select source material

Read the target page(s) in full. What to draw from each page type:
- Source pages: pipeline stages, motivations, results
- Concept pages: definitions, mechanisms, trade-offs, relationships
- Entity pages: what it is, why it matters, which concepts it connects to
- Material pages: comparisons, timelines, themes that span several sources

Aim for 8–15 cards per page. Favour material that students confuse with something
else, that has a "why" worth knowing, that involves a sequence or a decision point, or
that is a common exam mistake.

## Step 2: Choose card types

### Elaborative interrogation (most common)
"Why is this true?" or "Why was it designed this way?"

```
Why does a cellular automaton's next state depend only on a local neighbourhood rather than the whole grid?
?
Locality keeps each update cheap to compute, yet complex global patterns still arise from simple local interactions. That is emergence: the global behaviour is never programmed directly.
```

### Mechanism cards
Trace a process from a defined start to a defined end.

```
Given the current generation, what steps does Conway's Game of Life apply to produce the next one?
?
1. For each cell, count live neighbours in its 8-cell neighbourhood.
2. A live cell with 2-3 live neighbours survives; otherwise it dies.
3. A dead cell with exactly 3 live neighbours becomes alive.
4. Apply all updates simultaneously (synchronous update) to produce the next generation.
```

### Contrast cards
Separate two concepts that look alike but differ in an important way.

```
What is the key difference between agent-based modelling and system dynamics modelling?
?
ABM simulates individual agents with local rules and lets aggregate behaviour emerge bottom-up; system dynamics models aggregate stocks and flows directly with top-down differential/difference equations, without representing individuals.
```

### Failure-mode cards
"What breaks if this is missing or done wrong?"

```
What happens if a cellular automaton is updated asynchronously (cell-by-cell) instead of synchronously, without accounting for it in the rule design?
?
A cell's next state may be computed from neighbours that were already updated in the same tick, so the order of updates changes the outcome. Patterns that assume simultaneous updates (e.g. Game of Life gliders) break or behave unpredictably.
```

## Step 3: Quality rules

- **No definition-only cards.** Turn "What is X?" into an elaborative or contrast
  question.
- **Lead with the phenomenon.** Describe a concrete situation, then ask for its cause.
- **One idea per card.** Split a complex topic into several focused cards.
- **Wikilinks are allowed in the Obsidian deck** (e.g. `[[cellular-automaton]]`), but
  each card must be answerable without following the link.
- **Keep answers to 2–5 sentences**, short enough that the reader can check their
  recall against them at a glance.
- **Tag every card** as `#card/<subject> #card/<topic>`, taking `<subject>` from the
  schema's `subject` key (kebab-cased), so decks can be filtered.

## Step 4: Write the deck (Obsidian Spaced Repetition format)

Write all cards to one file, `<wiki_root>/<derived_dir>/<topic>-cue-cards.md`, grouped
under the section headers below. This file is the source of truth; Step 5 generates
the Anki export from it.

### Deck header
```markdown
#flashcards/<kebab-deck-name>
```

### Section headers (use as needed)
- `## Elaborative Interrogation`
- `## Mechanism`
- `## Contrast`
- `## Failure-Mode`
- `## Deck notes` (always last)

### Card structure
```markdown
Question text here (can span multiple sentences)?
?
Answer text here (can span multiple sentences or include numbered lists).
#card/<subject> #card/<topic>
```

Give each card its own tag line, holding tags and nothing else. The Anki export in
Step 5 treats that line as the end of the answer. An answer may therefore span blank
lines and lists, but tags appended to the end of an answer sentence are not exported.

### Deck notes
End with a `## Deck notes` section covering coverage, design choices, and why you
prioritised or left out particular topics.

Decks have no YAML frontmatter, following the Obsidian Spaced Repetition convention.
`lint` skips them in its frontmatter check.

## Step 5: Export to Anki

Run the converter on the deck you just wrote:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/cue-cards/scripts/to_anki_tsv.py" \
  <wiki_root>/<derived_dir>/<topic>-cue-cards.md
```

It writes `<topic>-cue-cards.anki.tsv` next to the deck. The file starts with a
`#separator:tab / #html:true / #tags column:3` header, then has one tab-separated
`Front\tBack\tTags` row per card. Wikilinks become plain text, and answer newlines
become `<br>` because Anki fields are HTML.

To import, the user picks **File → Import** in Anki and selects the `.tsv`. The header
tells Anki the separator, that fields are HTML and that column 3 holds tags, so no
column mapping is needed. Keep the `.tsv` out of git (`*.anki.tsv` in `.gitignore`):
it's personal, and the script can regenerate it at any time.

Mention the export file in your debrief so users on Anki know to import it.

### Keep review state out of the shared deck

The Obsidian Spaced Repetition plugin writes its scheduling state
(`<!--SR:!YYYY-MM-DD,interval,ease-->`) as an HTML comment under each card, inside the
tracked `.md` file. In a shared wiki, every review session then shows up as a git diff
carrying one person's progress data. Never commit those comments. Stripping them before
each commit isn't a workable routine either; stop them reaching the tracked file at all:

- **Recommend Anki for personal review by default.** Anki keeps review state in its own
  local collection, outside the repo, so reviewing there never touches the deck file.
- **To review in Obsidian against this vault**, the user marks the deck file
  `--skip-worktree` in their local clone first, which hides the plugin's inline writes
  from `git status` and `git diff`:
  ```bash
  git update-index --skip-worktree <wiki_root>/<derived_dir>/<topic>-cue-cards.md
  ```
  The setting is per clone and isn't shared through git. Before pulling upstream edits
  to that file, they run `git update-index --no-skip-worktree` on it, then set
  `--skip-worktree` again afterwards.
- If you see `<!--SR:...-->` comments in a deck you're editing or ingesting, strip them
  before committing. They aren't card content.

## Step 6: Connect the deck to the wiki

After writing the deck:
- Record which pages the cards came from.
- Update the relevant `index.md` and append to `<wiki_root>/log.md`.
- Recommend a first review interval of 1–3 days for new material, in either tool.
