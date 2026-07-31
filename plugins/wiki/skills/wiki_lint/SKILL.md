---
name: wiki_lint
description: Performs health checks on the CMAS wiki (wiki/) — contradictions, stale claims, orphans, dangling links, index drift, frontmatter issues. Suggests fixes and new sources/questions.
---

# Content Lint

Keeps `wiki/` healthy and compounding as more contributors add to it.

## Instructions

### 1. Run the deterministic checks first

```bash
python3 .claude/skills/wiki_lint/lint.py
```

The script reports:
- **Dangling links** — `[[…]]` targets with no matching page (excludes meta pages and
  frozen lint reports).
- **Orphans** — pages with no inbound links.
- **Index drift** — pages on disk but not listed in their section's `index.md`.
- **Frontmatter issues** — pages whose frontmatter doesn't match
  `.claude/wiki-schema.md` for their page type (missing `type`, missing `link` on
  source pages, etc). Cue-card decks are exempt (they intentionally omit frontmatter).

It exits non-zero if any issues are found, so it works in scripts and PR checks.

### 2. Then do the qualitative checks the script can't

- **Contradictions** — compare claims across pages on the same concept; flag with
  attribution rather than silently resolving.
- **Stale claims** — sources or concept pages superseded by newer ingests.
- **Copyright drift** — spot-check that source pages contain only links + original
  summary, not pasted copyrighted text (this is the one check worth doing by eye,
  since the script can't judge "is this a paraphrase").
- **Data gaps** — concepts mentioned but not yet ingested; suggest sources/questions.
- **Content quality** — source pages should have a "Topics covered" checklist;
  concept pages with a mathematical definition should have a `## Formula` block.

### 3. Report & fix

- Write the full report to `wiki/lint-reports/<YYYY-MM-DD>.md`.
- Fix mechanical issues directly (stub missing pages, update section indexes).
- Surface contradictions and data gaps to the user; don't silently resolve them.
- Append a one-line entry to `wiki/log.md`:
  `## [YYYY-MM-DD] lint | Issues found: X`.

### 4. Schema

- Enforce consistency with `.claude/wiki-schema.md`. The script encodes the
  frontmatter rules — update both together when the schema evolves.
- Run after every `wiki_ingest`, and periodically (e.g. as part of PR review) as
  the wiki grows with multiple contributors.
