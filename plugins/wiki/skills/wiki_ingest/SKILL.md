---
name: wiki_ingest
description: >
  Ingest a new source into a personal wiki. Use this skill whenever the user wants to
  add a source (lecture, paper, video, textbook chapter, external article) to the wiki,
  or says things like "ingest this", "add this to the wiki", "process this source", or
  "file this". Handles acquisition too: for recordings it obtains a transcript first,
  including fetching captions for YouTube-hosted video. It then writes the source page,
  creates/updates entity and concept pages, and refreshes the indexes and log. Always
  use this skill when a source needs to be incorporated into the wiki — even if the
  user just says "read this and add it". To turn ingested material into a long-form
  readable document, use `content-digest`, which calls this skill first.
---

# Wiki Ingest

Handles the full ingest pipeline for one source into a persistent, compounding wiki
(the Karpathy agentic-wiki pattern). The human curates sources and asks good questions;
you do the writing and maintenance.

## Wiki configuration — read this first

This skill is wiki-agnostic. Every path and policy below comes from the consuming
repo's `.claude/wiki-schema.md`, read from its YAML frontmatter. Read that file before
doing anything else, and fall back to these defaults for any key it omits:

| Key | Default | Meaning |
|---|---|---|
| `wiki_root` | `wiki` | Root directory of the vault. |
| `source_policy` | `link-only` | `link-only` records a URL and an original summary and never copies the source into the repo. `archive-raw` also copies the file into `raw_dir`. |
| `raw_dir` | `sources/raw` | Where archived originals live, relative to `wiki_root`. Only meaningful under `archive-raw`. |
| `derived_dir` | `materials` | Section holding worked examples, syntheses, and revision material. |
| `index_style` | `per-section` | `per-section` keeps an `index.md` in each section plus a root catalog; `root-only` keeps a single `index.md` at the wiki root. |
| `domains` | *(empty)* | Allowed `domain` values. When empty the wiki covers one subject and pages carry no `domain` field. When non-empty, every content page needs one. |
| `subject` | *(none)* | Display name of the subject, for page prose and generated documents. |
| `git_workflow` | `none` | `pr` opens a branch and PR after an ingest, `direct` commits to the current branch, `none` leaves version control alone. |

Under `source_policy: link-only` the constraint is not stylistic. That policy is set by
wikis whose sources are copyright and whose repo is public or shared. Read the source to
understand it, but never copy its text, images, or files into the repo — the page you
write is a link plus an original summary in your own words. Sources that are themselves
open (public papers, permissively licensed textbooks, the user's own notes) can be
described more liberally, but still summarise rather than pasting long verbatim blocks.

If `.claude/wiki-schema.md` does not exist, say so and offer to create one before
ingesting, rather than guessing at the wiki's conventions.

## Bundled files

- `scripts/fetch_transcript.py` — fetches YouTube captions as timestamp-anchored
  markdown. Used only from Step 2, via `references/youtube.md`.
- `references/youtube.md` — YouTube-specific transcript guidance. Read it only when the
  source is actually on YouTube; there is nothing in it for other hosts.

---

## Ingest pipeline

Work through these steps in order. Don't stop for confirmation between steps unless
you hit a genuine ambiguity — show the full result first, then discuss.

### Step 1 — Identify the source

Get (or ask for) the source's URL, title, and type (lecture, reading, paper, video,
textbook chapter, tutorial).

Derive a kebab-case slug from the title, e.g. `l04-cellular-automata.md` or
`wolfram-a-new-kind-of-science.md`. If the original filename is already descriptive and
kebab-case, keep it.

Then branch on `source_policy`. Under `link-only`, a local file the user supplies (a PDF
they have open, a downloaded deck) is read for understanding only and never copied into
the repo. Under `archive-raw`, copy it unmodified to `<wiki_root>/<raw_dir>/<slug>.<ext>`
so the original stays available for re-reading; keeping archived originals in their own
directory rather than beside the `.md` pages keeps the Obsidian graph clean.

### Step 2 — Obtain a transcript, if the source is a recording

Skip this step for text sources. For a lecture recording, talk, or podcast, you need a
transcript before you can read the source at all.

Establish where the transcript is coming from:

- **The user supplied one**, or the host provides a caption/transcript download — use it
  as-is.
- **The source is on YouTube** — read `references/youtube.md` and follow it. It covers
  URL cleaning, the fetch script, and the auto-caption pitfalls that silently corrupt
  word counts and timestamps.
- **Any other host, with no transcript available** — say so and ask how the user wants
  to proceed rather than guessing. Transcribing locally is an option but a slow one, and
  it is their call.

Where the transcript is written depends on `source_policy`. Under `archive-raw`, put it
in `<wiki_root>/<raw_dir>/<slug>-transcripts` and keep it — it is archived source
material like any other original. Under `link-only`, write it to a scratch directory
outside the repo (`$TMPDIR/<slug>-transcripts` is fine) and do not commit it. A
transcript is closer to the source material than a summary is, so under that policy it
is exactly the artifact that must not land in the repo. What you write from it is
original prose either way; the transcript is working material.

Whatever the source, the slides or paper are ground truth for names, notation, and
terminology. A transcript is a secondary record and is frequently wrong on exactly the
technical terms that matter.

### Step 3 — Read the source thoroughly

Build a mental model of:
- The main thesis or purpose
- Key concepts introduced or used
- Key entities mentioned (people, models, tools, software, papers)
- Important claims, results, or worked examples worth preserving
- Anything worth a short original quote (used sparingly, with attribution)

### Step 4 — Write the source page

Write `<wiki_root>/sources/<slug>.md`:

```markdown
---
title: <Title>
type: source
source_type: <lecture | reading | paper | video | textbook | tutorial | other>
link: <source URL>
domain: <required when `domains` is non-empty; omit otherwise>
tags: [<relevant tags>]
date: <YYYY-MM-DD>
---

# <Title>

## Overview
<2-4 paragraph original summary. What this source covers and why it matters. Written
for a reader who hasn't seen the source. Under `link-only`, never copy its wording.>

## Key concepts
<List concepts central to this source, each linked: [[concept-name]]. Create stubs in
Step 5 if the page doesn't exist yet — link to it anyway.>

## Key entities
<List entities central to this source (people, tools, models, papers cited), linked:
[[entity-name]]. Create stubs in Step 5 if needed.>

## Topics covered (revision checklist)
<Exhaustive but concise bullet list of every topic/method/definition mentioned. This
is the "have I covered everything" checklist for revision — don't duplicate the
Overview's depth, focus on completeness.>

## Notable claims / results
<Precise, citable bullets of the most important factual claims or findings.>

## Connections
<Cross-references to other wiki pages this source relates to, extends, or contradicts.>
```

### Step 5 — Update concept and entity pages

After writing the source page, identify every concept and entity it introduces,
defines, or meaningfully discusses.

For each:

1. **Check if a page already exists** in `<wiki_root>/concepts/` or `<wiki_root>/entities/`.
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

#### Entity page template (`<wiki_root>/entities/<slug>.md`)

```markdown
---
title: <Name>
type: entity
entity_type: <person | paper | model | software | organisation | dataset | other>
domain: <required when `domains` is non-empty; omit otherwise>
tags: []
date: <YYYY-MM-DD>
---

# <Name>

<1-2 sentence description of what/who this is.>

## Key facts
<Bullet list of the most important facts.>

## Relevance
<Why this entity matters in the context of `subject` (or of the wiki's scope).>

## Sources
- [[sources/<slug>]] — <one-line note on how this source relates to the entity>
```

#### Concept page template (`<wiki_root>/concepts/<slug>.md`)

```markdown
---
title: <Concept name>
type: concept
domain: <required when `domains` is non-empty; omit otherwise>
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
<Significance in the context of `subject` (or of the wiki's scope).>

## Relationships
<Links to related concepts and entities: [[other-concept]], [[entity-name]]>

## Sources
- [[sources/<slug>]] — <one-line note on what this source says about the concept>
```

### Step 6 — Update the indexes

Under `index_style: per-section`, each of `<wiki_root>/sources/index.md`,
`entities/index.md`, `concepts/index.md`, and `<derived_dir>/index.md` keeps its short
description at the top followed by a catalog, and `<wiki_root>/index.md` links to each
section. Under `root-only`, there is a single `<wiki_root>/index.md` holding every entry
grouped by section.

Either way, append new pages under a `## Pages` heading (create it if missing) and never
overwrite an existing catalog:

```markdown
## Pages
- [[<slug>]] — <one-line description> | added: YYYY-MM-DD
```

### Step 7 — Append to the log

Append a single entry to `<wiki_root>/log.md` (create the file with a `# Wiki Log`
header if it doesn't exist yet):

```markdown
## [<YYYY-MM-DD>] ingest | <source title>

- **Source page:** `<wiki_root>/sources/<slug>.md`
- **New concept pages:** <list or "none">
- **New entity pages:** <list or "none">
- **Updated pages:** <list or "none">
```

### Step 8 — Run wiki_lint

Always invoke the `wiki_lint` skill after writing all pages
(`python3 "${CLAUDE_PLUGIN_ROOT}/skills/wiki_lint/lint.py"`). Resolve any new dangling
links or index drift it reports before closing out the ingest. Append the lint result to
`<wiki_root>/log.md` and write the full report to
`<wiki_root>/lint-reports/<YYYY-MM-DD>.md`.

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
  synthesise, don't transcribe, and respect `source_policy` on wording.
- **Concept and entity pages** should be updated on every ingest that touches them,
  not just when the source is primarily about them.
- **Cross-references** should be bidirectional where meaningful.
- **Contradictions** should be flagged explicitly, not silently overwritten.

## Version control

Follow `git_workflow` from the schema.

Under `pr`, the wiki is versioned in a shared repo and ingests land as reviewed
branches:

```bash
git checkout -b ingest/<slug>
git add <wiki_root>
git commit -m "ingest: <source title> — added <N> concepts, <M> entities"
git push -u origin ingest/<slug>
```

Then open a PR (check the repo's `CONTRIBUTING.md`). Don't push directly to the default
branch unless the user explicitly says to.

Under `direct`, commit to the current branch with the same message format and no PR.
Under `none`, leave version control alone — the wiki may not be a git repo at all.
