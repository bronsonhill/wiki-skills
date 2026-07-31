---
name: cue-cards
description: >
  Generate high-quality, spaced-repetition-ready cue cards from the CMAS wiki
  (wiki/). Use this skill when the user wants flashcards for revision from
  any content page (source, concept, entity, or material). Cards follow cognitive
  science principles (elaborative interrogation, desirable difficulty, contrast,
  failure modes) and are produced in a tool-agnostic canonical format, then rendered
  to both the Obsidian Spaced Repetition plugin format and an Anki-importable TSV
  export — so cards work whichever SRS tool the contributor or reader uses. Trigger
  on phrases like "make cue cards", "generate flashcards", "quiz me on", "revision
  cards for", "export to anki", or "turn this page into cards".
---

# Cue Card Generator

Creates cue cards optimised for long-term retention and genuine understanding from
`wiki/`. The card *content* is tool-agnostic; two renderers turn it into whatever
format the reader's SRS tool needs — Obsidian Spaced Repetition (native `.md`, lives
in the wiki, wikilinks preserved) or Anki (`.tsv` import, wikilinks stripped since
Anki has no concept of them).

## Step 1 — Select source material

Read the target content page(s) thoroughly:
- Source pages → focus on pipeline stages, motivations, results
- Concept pages → focus on definitions, mechanisms, trade-offs, relationships
- Entity pages → focus on what it is, why it matters, how it relates to concepts
- Material pages → focus on comparisons, timelines, cross-cutting themes

Identify 8-15 high-value cards per page. Prioritise material that is:
- Frequently confused
- Has an important "why" explanation
- Involves a sequence or decision point
- Represents a common exam/revision pitfall

## Step 2 — Choose card type

### Elaborative Interrogation (most common)
"Why is this true?" or "Why does this design choice exist?"

```
Why does a cellular automaton's next state depend only on a local neighbourhood rather than the whole grid?
?
Locality keeps the update rule computationally tractable and lets complex global behaviour emerge from simple local interactions — the defining feature of emergence in ABMs, rather than being explicitly programmed.
```

### Mechanism cards
Trace a process from start to finish with clear boundaries.

```
Starting from an initial population and ending at a steady state, what are the update steps of Conway's Game of Life on each tick?
?
1. For each cell, count live neighbours in its 8-cell neighbourhood.
2. A live cell with 2-3 live neighbours survives; otherwise it dies.
3. A dead cell with exactly 3 live neighbours becomes alive.
4. Apply all updates simultaneously (synchronous update) to produce the next generation.
```

### Contrast cards
Compare two similar but importantly different concepts.

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
The next state calculation for one cell may read already-updated neighbours from the same tick, coupling update order to the outcome. Patterns that assume simultaneous updates (e.g. Game of Life gliders) break or behave unpredictably.
```

## Step 3 — Quality rules

- **No definition-only cards.** Convert "What is X?" into an elaborative or contrast
  question.
- **Embed the phenomenon.** Start with a concrete situation before asking for the
  cause.
- **One idea per card.** Split complex topics into multiple focused cards.
- **Wikilinks are fine in the canonical/Obsidian form** (e.g. `[[cellular-automaton]]`)
  but keep each card self-contained — a reader shouldn't need to follow the link to
  answer it.
- **Keep answers concise but complete.** 2-5 sentences max, quickly self-verifiable.
- **Tag every card** in the format `#card/cmas #card/<topic>` so decks can be filtered.

## Step 4 — Write the canonical deck (Obsidian Spaced Repetition format)

Output cards grouped under standard section headers, in a single
`wiki/materials/<topic>-cue-cards.md` file. This is the source of truth; the Anki
export in Step 5 is generated from it.

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
#card/cmas #card/<topic>
```

### Deck notes
End with a `## Deck notes` section explaining design choices, coverage, and why
certain topics were prioritised or excluded.

Cue-card decks intentionally have no YAML frontmatter (Obsidian Spaced Repetition
convention) — `wiki_lint` exempts them from the frontmatter check.

## Step 5 — Export to Anki

Run the converter on the deck you just wrote:

```bash
python3 .claude/skills/cue-cards/scripts/to_anki_tsv.py wiki/materials/<topic>-cue-cards.md
```

This writes `wiki/materials/<topic>-cue-cards.anki.tsv` next to it — a
tab-separated `Front\tBack\tTags` file with wikilinks stripped to plain text and
answer newlines converted to `<br>` (Anki fields are HTML). To import in Anki:
**File → Import**, select the `.tsv`, map the three columns to Front/Back/Tags, and
set the field separator to Tab. The `.tsv` is gitignored (`*.anki.tsv`) — it's a
personal, regenerable artifact, not wiki content.

Mention the export file exists in your debrief so the user knows to import it if they
use Anki instead of Obsidian.

### Don't let personal review state pollute the shared deck

The Obsidian Spaced Repetition plugin writes its scheduling state
(`<!--SR:!YYYY-MM-DD,interval,ease-->`) as an inline comment directly under each
card, inside the tracked `.md` file. Since `wiki/materials/` is shared, that turns
every personal review session into a git diff full of someone else's progress data
on a shared file. Never commit those comments, and don't strip-then-recommit them
as a normal workflow either — prevent them from landing in the first place:

- **Recommend Anki for personal review by default.** Its review state lives in
  Anki's own local collection (outside the repo entirely), so reviewing there
  never touches the tracked deck.
- **If someone wants to review in Obsidian against this vault**, they should mark
  the deck file `--skip-worktree` in their local clone first, so the plugin's
  inline writes stay local and invisible to `git status`/`diff`:
  ```bash
  git update-index --skip-worktree wiki/materials/<topic>-cue-cards.md
  ```
  This is a local-only, per-clone setting (not shared via git). They'll need to
  `git update-index --no-skip-worktree` on that file before pulling upstream
  edits to it, then re-apply `--skip-worktree` afterwards.
- If you (the agent) ever see `<!--SR:...-->` comments in a deck file you're
  editing or ingesting, strip them before committing — they're not part of the
  card content.

## Step 6 — Integration with the wiki

After generating cards:
- Note which content pages the cards are derived from.
- Update `wiki/materials/index.md` and append to `wiki/log.md`.
- Recommend an initial SRS interval of 1-3 days for new material, in either tool.

---

**Trigger phrases:** "make cue cards from", "generate flashcards for", "create
revision cards on", "quiz me on the page about", "export cards to anki", "turn
[[page]] into spaced repetition cards".
