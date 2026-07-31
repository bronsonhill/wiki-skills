---
name: wiki_lint
description: Performs health checks on a personal wiki — contradictions, stale claims, orphans, dangling links, index drift, frontmatter and domain issues. Suggests fixes and new sources/questions.
---

# Wiki Lint

Keeps the wiki healthy and compounding as it grows.

Paths and policies come from the consuming repo's `.claude/wiki-schema.md` — see the
configuration table in `wiki_ingest` for the full set of keys. This skill reads
`wiki_root`, `derived_dir`, `index_style`, `domains`, and `source_policy`.

## Instructions

### 1. Run the deterministic checks first

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/wiki_lint/lint.py"
```

The script reads the schema itself, so it needs no arguments when run from anywhere
inside the repo. Pass an explicit wiki directory as the first argument to override.

It reports:
- **Dangling links** — `[[…]]` targets with no matching page (excludes meta pages and
  frozen lint reports).
- **Orphans** — pages with no inbound links.
- **Index drift** — pages on disk but not listed in the index that should catalog them
  (per-section or root, following `index_style`).
- **Frontmatter issues** — pages whose frontmatter doesn't match the schema for their
  page type (missing `type`, missing `link` on source pages, etc). Cue-card decks are
  exempt, since they intentionally omit frontmatter.
- **Domain issues** — only when `domains` is non-empty: content pages missing a
  `domain`, or using a top-level domain outside the allowed set.
- **Possible name collisions across domains** — near-duplicate filenames in the same
  section whose domains don't overlap. Decide consciously whether to merge them into
  one shared page or rename one.

It exits non-zero if any issues are found, so it works in scripts and PR checks.

### 2. Then do the qualitative checks the script can't

- **Contradictions** — compare claims across pages on the same concept; flag with
  attribution rather than silently resolving.
- **Stale claims** — sources or concept pages superseded by newer ingests.
- **Source policy drift** — under `source_policy: link-only`, spot-check that source
  pages hold links plus original summary rather than pasted copyrighted text. This is
  worth doing by eye, since the script can't judge whether something is a paraphrase.
- **Data gaps** — concepts mentioned but not yet ingested; suggest sources/questions.
- **Content quality** — source pages should have a "Topics covered" checklist;
  concept pages with a mathematical definition should have a `## Formula` block.

### 3. Report & fix

- Write the full report to `<wiki_root>/lint-reports/<YYYY-MM-DD>.md`.
- Fix mechanical issues directly (stub missing pages, update the indexes).
- Surface contradictions and data gaps to the user; don't silently resolve them.
- Append a one-line entry to `<wiki_root>/log.md`:
  `## [YYYY-MM-DD] lint | Issues found: X`.

### 4. Schema

- Enforce consistency with `.claude/wiki-schema.md`. The script encodes the frontmatter
  rules — update both together when the schema evolves.
- Run after every `wiki_ingest`, and periodically (weekly, or as part of PR review) as
  the wiki grows with multiple contributors.
