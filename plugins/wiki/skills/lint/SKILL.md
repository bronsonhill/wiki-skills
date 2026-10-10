---
name: lint
description: >
  Run health checks on a personal wiki. A script finds dangling links, orphans, index
  drift, and frontmatter and domain errors; you then read for contradictions, stale
  claims, source-policy drift and gaps. Fixes the mechanical problems and reports the
  rest. Use after an ingest, before merging wiki changes, or when the user asks to
  lint, audit, check or clean up the wiki.
---

# Wiki Lint

A wiki with many ingests and several contributors collects broken links, unindexed
pages, and claims that later sources overturned. This skill finds them. A script covers
the mechanical checks; the rest need you to read pages.

Paths and policies come from the consuming repo's `.claude/wiki-schema.md` (the full
key table is in `ingest`). This skill reads `wiki_root`, `derived_dir`, `index_style`,
`domains` and `source_policy`.

## Instructions

### 1. Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lint/lint.py"
```

The script reads the schema itself and needs no arguments from anywhere inside the
repo. Pass a wiki directory as the first argument to override.

It reports:
- **Dangling links:** `[[…]]` targets with no matching page (meta pages and frozen lint
  reports are excluded).
- **Orphans:** pages nothing links to.
- **Index drift:** pages on disk that are missing from the index that should list them
  (per-section or root, following `index_style`).
- **Frontmatter issues:** pages whose frontmatter doesn't match the schema for their
  type (no `type`, a source page with no `link`, no `description`, etc.). Cue-card
  decks are skipped,
  since they have no frontmatter by design.
- **Domain issues**, only when `domains` is non-empty: content pages with no `domain`,
  or with a top-level domain outside the allowed set.
- **Possible name collisions across domains:** near-duplicate filenames in one section
  whose domains don't overlap. Decide whether they describe the same thing (merge into
  one shared page) or different things (rename one).

It exits non-zero when it finds anything, so it can gate a script or a PR check.

### 2. Check what the script can't

- **Contradictions:** compare claims across pages about the same concept. Flag each
  with the pages involved; don't pick a winner yourself.
- **Stale claims:** source or concept pages that a newer ingest superseded.
- **Source-policy drift:** under `source_policy: link-only`, open a sample of source
  pages and check they hold a link and an original summary, not pasted text. The
  script can't tell a paraphrase from a copy.
- **Data gaps:** concepts mentioned with no page or source behind them. Suggest sources
  or questions that would fill them.
- **Content quality:** every source page needs a "Topics covered" checklist, and every
  concept page with a mathematical definition needs a `## Formula` section.

### 3. Report and fix

- Write the full report to `<wiki_root>/lint-reports/<YYYY-MM-DD>.md`.
- Fix mechanical problems directly: stub missing pages, add pages to the indexes, and
  fill a missing `description` from the page's index entry (or write one line from the
  page's opening definition if it has no entry).
- Report contradictions and data gaps to the user instead of resolving them.
- Append one line to `<wiki_root>/log.md`:
  `## [YYYY-MM-DD] lint | Issues found: X`.

### 4. When to run

- After every `ingest`, and on a schedule (weekly, or in PR review) once several people
  contribute.
- `lint.py` encodes the frontmatter rules from `.claude/wiki-schema.md`. When the
  schema changes, update the script in the same change.
