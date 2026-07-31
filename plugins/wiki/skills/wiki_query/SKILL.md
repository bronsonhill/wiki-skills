---
name: wiki_query
description: Queries the CMAS wiki (wiki/) for answers, synthesizing from pages with citations. Files valuable outputs back to wiki/materials/. Uses wiki/index.md first for navigation.
---

# Content Query

Enables synthesis over the persistent `wiki/` wiki instead of raw RAG or re-reading
copyright-protected course material from scratch each time.

## Instructions

### 1. Search

- Read `wiki/index.md` first, then the relevant section index
  (`wiki/concepts/index.md`, etc.) to identify candidate pages.
- Grep for keywords across `wiki/` if the index doesn't surface enough.
- Drill into specific source/entity/concept/material pages.

### 2. Synthesize

- Combine information across pages, note contradictions explicitly if any exist.
- Answer with wikilinks/citations back to the pages used — every non-trivial claim
  should be traceable to a `[[sources/...]]` or `[[concepts/...]]` page.
- Output formats: markdown summary, table, or (for revision) a `materials/` page.

### 3. File back

- If the synthesis is genuinely valuable (a new comparison, a worked derivation, an
  exam-relevant summary), save it as a new page under `wiki/materials/`.
- Update the relevant section `index.md` and append to `wiki/log.md`:
  `## [YYYY-MM-DD] query | <topic>`.
- Add cross-references from/to the concept and entity pages involved.

### 4. Schema

- Respect `.claude/wiki-schema.md` conventions, including required frontmatter on
  any new page.

### 5. Health

- If the query surfaces a gap (a concept mentioned nowhere, a stale/contradicted
  claim), flag it and suggest running `wiki_lint` or ingesting a new source.
