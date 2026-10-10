---
name: query
description: >
  Answer questions from a personal wiki by synthesising across its pages, with a
  citation for every claim, and file useful answers back as new pages. Use when the
  user asks something the wiki should be able to answer ("what does the wiki say about
  X", "compare X and Y", "summarise what we have on Z"), or wants a comparison or
  revision summary built from existing pages. Navigates from the wiki index first.
---

# Wiki Query

Answer questions from the wiki's existing pages instead of rereading the original
sources or searching raw files. The wiki already holds summaries, definitions and
cross-links; build the answer from those.

Paths come from the consuming repo's `.claude/wiki-schema.md` (the configuration table
is in `ingest`). This skill reads `wiki_root`, `derived_dir`, `index_style` and
`domains`.

**Outside the wiki's repo** (no `.claude/wiki-schema.md` above the working directory),
use the `wiki` MCP server's tools in place of file reads: `wiki_index` for step 1's
index, `wiki_search` for its grep, `wiki_read` for the pages. Step 2 applies as
written, citing page ids. The server is read-only, so skip step 3 and tell the user
which answers are worth filing from inside the wiki's repo. If the tools aren't
available, run the `connect` skill.

## Instructions

### 1. Find the pages

- Start at `<wiki_root>/index.md`. Under `index_style: per-section`, follow it into the
  relevant section index (`concepts/index.md`, etc.) to find candidate pages.
- If the index turns up too little, grep the wiki for keywords.
- Read the candidate source, entity, concept and `<derived_dir>` pages in full.
- When `domains` is set and the question concerns one subject, restrict the search to
  pages whose `domain` matches. Cross-domain answers are allowed, since the graph is
  shared on purpose, but tell the user when an answer draws on another domain.
- Where pages have frontmatter, a Dataview query narrows the search quickly, e.g.
  `TABLE type FROM "concepts" WHERE contains(domain, "academic/nlp")`.

### 2. Write the answer

- Combine what the pages say. When two pages disagree, name both pages and state what
  each claims.
- Cite as you go: every non-trivial claim links to the `[[sources/...]]` or
  `[[concepts/...]]` page it came from.
- Pick the format the question calls for: prose, a table, or, for revision, a
  `<derived_dir>/` page.

### 3. File it back

- Save the answer as a new page under `<wiki_root>/<derived_dir>/` when someone would
  want to find it again: a comparison no existing page makes, a worked derivation, an
  exam-focused summary. One-off lookups don't need a page.
- Give the new page the frontmatter `.claude/wiki-schema.md` requires, including
  `description` (the same line as its index entry) and `domain` when the wiki uses it.
- Update the relevant `index.md` and append to `<wiki_root>/log.md`:
  `## [YYYY-MM-DD] query | <topic>`.
- Link the new page from the concept and entity pages it draws on, and link back.

### 4. Report gaps

- If the question exposes a gap (a concept with no page, a claim that looks stale or
  that another page contradicts), tell the user and suggest running `lint` or ingesting
  a source that covers it.
