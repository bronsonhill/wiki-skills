---
name: wiki_ingest
description: >
  Ingest a new source into the CMAS wiki (wiki/). Use this skill whenever
  the user wants to add a source (Canvas lecture, paper, video, textbook chapter,
  external article) to the wiki, or says things like "ingest this", "add this to the
  wiki", "process this source", or "file this". The skill writes a source stub (link +
  original summary — never a copy of copyrighted material), then creates/updates
  entity and concept pages, and refreshes the section indexes and wiki/log.md.
  Always use this skill when a source needs to be incorporated into wiki/ — even
  if the user just says "read this and add it".
---

# Content Ingest

Handles the full ingest pipeline for one source into the CMAS wiki. The wiki
is a persistent, compounding knowledge base for the Computational Modelling and
Simulation subject, built collaboratively by students and maintained largely by the
agent. See `.claude/wiki-schema.md` for the schema this skill implements.

**Copyright constraint — read this first:** University of Melbourne course material
(lecture slides, recordings, PDFs) is copyright and this repo is public. You may read
the source to understand it, but never copy its text, images, or files into the repo.
The source page you write is a link plus an original summary in your own words.
Exception: sources that are themselves open (public papers, textbooks with a
permissive licence, your own notes) can be described more liberally, but still don't
paste large verbatim blocks — summarise.

---

## Ingest pipeline

Work through these steps in order. Don't stop for confirmation between steps unless
you hit a genuine ambiguity — show the full result first, then discuss.

### Step 1 — Identify the source

Get (or ask for) the Canvas/external URL, the source's title, and its type (lecture,
reading, paper, video, textbook chapter, tutorial). If given a local file (e.g. a PDF
the user has open), read it for understanding only — it is not copied into the repo.

Derive a kebab-case slug from the title, e.g. `l04-cellular-automata.md` or
`wolfram-a-new-kind-of-science.md`.

### Step 2 — Read the source thoroughly

Build a mental model of:
- The main thesis or purpose
- Key concepts introduced or used
- Key entities mentioned (people, models, tools, software, papers)
- Important claims, results, or worked examples worth preserving
- Anything worth a short original quote (used sparingly, with attribution)

### Step 3 — Write the source page

Write `wiki/sources/<slug>.md`:

```markdown
---
title: <Title>
type: source
source_type: <lecture | reading | paper | video | textbook | tutorial | other>
link: <Canvas URL or external URL>
tags: [<relevant tags>]
date: <YYYY-MM-DD>
---

# <Title>

## Overview
<2-4 paragraph original summary. What this source covers and why it matters. Written
for a reader who hasn't seen the source — never copy its wording.>

## Key concepts
<List concepts central to this source, each linked: [[concept-name]]. Create stubs in
Step 4 if the page doesn't exist yet — link to it anyway.>

## Key entities
<List entities central to this source (people, tools, models, papers cited), linked:
[[entity-name]]. Create stubs in Step 4 if needed.>

## Topics covered (revision checklist)
<Exhaustive but concise bullet list of every topic/method/definition mentioned. This
is the "have I covered everything" checklist for revision — don't duplicate the
Overview's depth, focus on completeness.>

## Notable claims / results
<Precise, citable bullets of the most important factual claims or findings.>

## Connections
<Cross-references to other wiki/ pages this source relates to, extends, or
contradicts.>
```

### Step 4 — Update concept and entity pages

After writing the source page, identify every concept and entity it introduces,
defines, or meaningfully discusses.

For each:

1. **Check if a page already exists** in `wiki/concepts/` or `wiki/entities/`.
2. **If it exists:** append a `## Sources` entry linking to the new source. Update the
   body if the new source adds meaningful new information or refines the definition —
   note contradictions explicitly rather than silently overwriting.
3. **If it doesn't exist:** create a stub page (templates below). Don't leave a
   concept or entity mentioned in the source without a page.

The distinction:
- **Entity** — a specific named thing you can point to: a person, tool, model,
  software package, paper, organisation. (NetLogo, John Conway, a specific paper)
- **Concept** — an idea, mechanism, technique, or phenomenon you explain rather than
  identify. (cellular automaton, emergence, agent-based model, Monte Carlo method)

When in doubt: can you point at the specific thing? → Entity. Do you need to explain
what it means? → Concept.

#### Entity page template (`wiki/entities/<slug>.md`)

```markdown
---
title: <Name>
type: entity
entity_type: <person | paper | model | software | organisation | dataset | other>
tags: []
date: <YYYY-MM-DD>
---

# <Name>

<1-2 sentence description of what/who this is.>

## Key facts
<Bullet list of the most important facts.>

## Relevance to CMAS
<Why this entity matters in the context of computational modelling and simulation.>

## Sources
- [[sources/<slug>]] — <one-line note on how this source relates to the entity>
```

#### Concept page template (`wiki/concepts/<slug>.md`)

```markdown
---
title: <Concept name>
type: concept
tags: []
date: <YYYY-MM-DD>
---

# <Concept name>

<1-3 sentence definition. Precise and technical where appropriate.>

## How it works
<Explanation of the mechanism or idea. Use concrete examples from sources.>

## Formula
<If the concept has a mathematical definition (e.g. a transition rule, an update
equation), add this section using proper Obsidian LaTeX: `$...$` inline, `$$...$$`
block.>

## Why it matters
<Significance in the context of modelling and simulation.>

## Relationships
<Links to related concepts and entities: [[other-concept]], [[entity-name]]>

## Sources
- [[sources/<slug>]] — <one-line note on what this source says about the concept>
```

### Step 5 — Update section indexes

Each of `wiki/sources/index.md`, `wiki/entities/index.md`,
`wiki/concepts/index.md` keeps its short description at the top, followed by a
catalog. Append new pages under a `## Pages` heading (create it if missing):

```markdown
## Pages
- [[<slug>]] — <one-line description> | added: YYYY-MM-DD
```

### Step 6 — Append to wiki/log.md

Append a single entry (create the file with a `# Content Log` header if it doesn't
exist yet):

```markdown
## [<YYYY-MM-DD>] ingest | <source title>

- **Source page:** `wiki/sources/<slug>.md`
- **New concept pages:** <list or "none">
- **New entity pages:** <list or "none">
- **Updated pages:** <list or "none">
```

### Step 7 — Run wiki_lint

Always invoke the `wiki_lint` skill after writing all pages
(`python3 .claude/skills/wiki_lint/lint.py`). Resolve any new dangling links or
index drift it reports before closing out the ingest. Append the lint result to
`wiki/log.md` and write the full report to
`wiki/lint-reports/<YYYY-MM-DD>.md`.

This is non-optional — ingests that skip linting accumulate orphans and index drift
quickly, especially with multiple contributors working in parallel.

---

## After the ingest

Give a brief, conversational debrief:

1. What the source is and what it contributes to the wiki
2. Which pages were created or updated (summarised, not exhaustive)
3. Any open questions, gaps, or contradictions noticed
4. Suggested follow-up sources worth ingesting

The human may want to correct the summary, redirect emphasis, or ask follow-up
questions — revise before closing out.

---

## Quality standards

- **Summaries** should be genuinely useful to a reader who hasn't seen the source —
  synthesise, don't transcribe, and never copy copyrighted wording.
- **Concept and entity pages** should be updated on every ingest that touches them,
  not just when the source is primarily about them.
- **Cross-references** should be bidirectional where meaningful.
- **Contradictions** should be flagged explicitly, not silently overwritten.

## Git / PR workflow

This repo is public and collaborative — `wiki/` is not a separate wiki repo, it's
versioned in this same repo via normal PRs. After an ingest:

```bash
git checkout -b ingest/<slug>
git add wiki/sources/<slug>.md wiki/concepts/* wiki/entities/* \
  wiki/*/index.md wiki/log.md wiki/lint-reports/*
git commit -m "ingest: <source title> — added <N> concepts, <M> entities"
git push -u origin ingest/<slug>
```

Then open a PR (see `CONTRIBUTING.md`). Don't push directly to `main` unless the user
explicitly says to.
