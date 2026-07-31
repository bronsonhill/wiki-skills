---
name: wiki_query
description: Queries a personal wiki for answers, synthesizing across pages with citations. Files valuable outputs back as new pages. Uses the wiki index first for navigation.
---

# Wiki Query

Enables synthesis over the persistent wiki instead of raw RAG or re-reading source
material from scratch each time.

Paths come from the consuming repo's `.claude/wiki-schema.md` — see the configuration
table in `wiki_ingest`. This skill reads `wiki_root`, `derived_dir`, `index_style`, and
`domains`.

## Instructions

### 1. Search

- Read `<wiki_root>/index.md` first. Under `index_style: per-section`, follow it into
  the relevant section index (`concepts/index.md`, etc.) to identify candidate pages.
- Grep for keywords across the wiki if the index doesn't surface enough.
- Drill into specific source/entity/concept/`<derived_dir>` pages.
- When `domains` is configured and the question is about one subject, filter to pages
  whose frontmatter `domain` matches. Cross-domain questions are fine — the graph is
  shared on purpose — but say when you are crossing a boundary.

### 2. Synthesize

- Combine information across pages, note contradictions explicitly if any exist.
- Answer with wikilinks/citations back to the pages used — every non-trivial claim
  should be traceable to a `[[sources/...]]` or `[[concepts/...]]` page.
- Output formats: markdown summary, table, or (for revision) a `<derived_dir>/` page.

### 3. File back

- If the synthesis is genuinely valuable (a new comparison, a worked derivation, an
  exam-relevant summary), save it as a new page under `<wiki_root>/<derived_dir>/`.
- Update the relevant `index.md` and append to `<wiki_root>/log.md`:
  `## [YYYY-MM-DD] query | <topic>`.
- Add cross-references from/to the concept and entity pages involved.

### 4. Schema

- Respect `.claude/wiki-schema.md` conventions, including required frontmatter on any
  new page, and set `domain` when the wiki uses it.
- Where frontmatter supports it, Dataview queries are a fast way to scope a search, e.g.
  `TABLE type FROM "concepts" WHERE contains(domain, "academic/nlp")`.

### 5. Health

- If the query surfaces a gap (a concept mentioned nowhere, a stale/contradicted
  claim), flag it and suggest running `wiki_lint` or ingesting a new source.
