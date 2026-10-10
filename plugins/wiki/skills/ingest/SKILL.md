---
name: ingest
description: >
  Ingest a new source into a personal wiki. Use whenever the user wants to add a source
  (lecture, paper, video, textbook chapter, external article) to the wiki, or says
  things like "ingest this", "add this to the wiki", "process this source", "file this",
  or just "read this and add it". Handles acquisition: for recordings it gets a
  transcript first, including fetching captions for YouTube video. Then it writes the
  source page, creates or updates entity and concept pages, and updates the indexes and
  log. To turn ingested material into a long-form readable document, use
  `content-digest`, which calls this skill first.
---

# Wiki Ingest

Runs the full ingest of one source into a persistent wiki that grows with every source
(the Karpathy agentic-wiki pattern). The user picks sources and asks questions; you
write and maintain the pages.

## Wiki configuration (read first)

This skill works on any wiki with a schema file. Every path and policy below comes from
the YAML frontmatter of the consuming repo's `.claude/wiki-schema.md`. Read that file
before anything else, and use these defaults for any key it omits:

| Key | Default | Meaning |
|---|---|---|
| `wiki_root` | `wiki` | Root directory of the vault. |
| `source_policy` | `link-only` | `link-only` records a URL and an original summary and never copies the source into the repo. `archive-raw` also copies the file into `raw_dir`. |
| `raw_dir` | `sources/raw` | Where archived originals live, relative to `wiki_root`. Used only under `archive-raw`. |
| `derived_dir` | `materials` | Section for worked examples, syntheses and revision material. |
| `index_style` | `per-section` | `per-section` keeps an `index.md` in each section plus a root catalog; `root-only` keeps a single `index.md` at the wiki root. |
| `domains` | *(empty)* | Allowed `domain` values. When empty, the wiki covers one subject and pages carry no `domain` field. When set, every content page needs one. |
| `subject` | *(none)* | Display name of the subject, used in page prose and generated documents. |
| `git_workflow` | `none` | `pr` opens a branch and PR after an ingest, `direct` commits to the current branch, `none` leaves version control alone. |

Wikis set `source_policy: link-only` when their sources are under copyright and the
repo is public or shared, so treat it as a legal limit. Read the source to understand
it, but never copy its text, images or files into the repo. The page you write is a
link plus a summary in your own words. Open sources (public papers, permissively
licensed textbooks, the user's own notes) allow more latitude, but summarise those too
instead of pasting long passages.

If `.claude/wiki-schema.md` doesn't exist, tell the user and offer to create one before
ingesting. Don't guess the wiki's conventions.

## Bundled files

- `scripts/fetch_transcript.py` fetches YouTube captions as timestamped markdown. Only
  Step 2 uses it, via `references/youtube.md`.
- `references/youtube.md` holds the YouTube-specific transcript steps. Read it only
  when the source is on YouTube.

---

## Ingest pipeline

Work through the steps in order without stopping for confirmation. Stop only when
something is ambiguous enough that a wrong guess would mean rewriting pages. Show the
finished result, then discuss.

### Step 1: Identify the source

Get (or ask for) the source's URL, title and type (lecture, reading, paper, video,
textbook chapter, tutorial).

Derive a kebab-case slug from the title, e.g. `l04-cellular-automata.md` or
`wolfram-a-new-kind-of-science.md`. If the original filename is already descriptive and
kebab-case, keep it.

Then check `source_policy`. Under `link-only`, read any local file the user supplies (a
PDF they have open, a downloaded deck) for understanding only, and never copy it into
the repo. Under `archive-raw`, copy it unmodified to `<wiki_root>/<raw_dir>/<slug>.<ext>`
so the original is there to reread. A separate directory keeps archived files out of
the Obsidian graph view.

### Step 2: Get a transcript, if the source is a recording

Skip this step for text sources. A lecture recording, talk or podcast can't be read
until you have a transcript.

Work out where the transcript will come from:

- **The user supplied one**, or the host offers a caption or transcript download: use
  it as-is.
- **The source is on YouTube:** read `references/youtube.md` and follow it. It covers
  URL cleaning, the fetch script, and the dedupe check. When the dedupe fails, word
  counts and timestamps come out wrong with no error.
- **Any other host, with no transcript available:** tell the user and ask how to
  proceed. Local transcription works but is slow, and whether to spend that time is
  their decision.

Where the transcript goes depends on `source_policy`. Under `archive-raw`, write it to
`<wiki_root>/<raw_dir>/<slug>-transcripts` and keep it, like any other archived
original. Under `link-only`, write it to a scratch directory outside the repo
(`$TMPDIR/<slug>-transcripts` works) and don't commit it. A transcript reproduces the
source almost word for word, which is what `link-only` exists to keep out of the repo.
The pages you write from it are original prose under either policy.

The slides or the paper are the authority on names, notation and terminology.
Transcripts get technical terms wrong more often than anything else ("peratron" for
Perceptron), so check each term against the deck.

### Step 3: Read the source thoroughly

Before writing, work out:
- The main thesis or purpose
- The key concepts it introduces or uses
- The key entities it mentions (people, models, tools, software, papers)
- The claims, results and worked examples worth keeping
- Any short passage worth quoting (sparingly, with attribution)

### Step 4: Write the source page

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
<2-4 paragraph original summary of what this source covers and why it matters, for a
reader who hasn't seen it. Under `link-only`, never copy its wording.>

## Key concepts
<Concepts central to this source, each linked: [[concept-name]]. Link even if the page
doesn't exist yet; Step 5 creates it.>

## Key entities
<Entities central to this source (people, tools, models, papers cited), linked:
[[entity-name]]. Step 5 creates any missing pages.>

## Topics covered (revision checklist)
<Short bullets for every topic, method and definition the source mentions, so a reader
can check they have covered everything. Aim for breadth; the Overview carries the
explanation.>

## Notable claims / results
<Precise, citable bullets for the most important claims or findings.>

## Connections
<Links to other wiki pages this source relates to, extends or contradicts.>
```

### Step 5: Update concept and entity pages

After writing the source page, list every concept and entity the source introduces,
defines or discusses at more than a passing mention.

For each one:

1. **Check for an existing page** in `<wiki_root>/concepts/` or `<wiki_root>/entities/`.
2. **If it exists:** append a `## Sources` entry linking to the new source. Edit the
   body if the source adds facts or sharpens the definition. If it contradicts the
   page, record both claims with their sources instead of overwriting.
3. **If it doesn't exist:** create a stub from the templates below. Every concept and
   entity the source discusses gets a page.

To tell them apart:
- **Entity:** a specific named thing: a person, tool, model, software package, paper,
  organisation (NetLogo, John Conway, a specific paper).
- **Concept:** an idea, mechanism, technique or phenomenon that needs explaining
  (cellular automaton, emergence, agent-based model, Monte Carlo method).

If you can point at the specific thing, it's an entity. If you have to explain what it
means, it's a concept.

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

<1-2 sentences on what or who this is.>

## Key facts
<Bullets for the most important facts.>

## Relevance
<Why this entity matters to `subject` (or to the wiki's scope).>

## Sources
- [[sources/<slug>]] — <one line on how this source relates to the entity>
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

<1-3 sentence definition, precise and technical where the subject calls for it.>

## How it works
<The mechanism or idea, with concrete examples from the sources.>

## Formula
<Only if the concept has a mathematical definition (a transition rule, an update
equation). Use Obsidian LaTeX: `$...$` inline, `$$...$$` block.>

## Why it matters
<Why this concept matters to `subject` (or to the wiki's scope).>

## Relationships
<Links to related concepts and entities: [[other-concept]], [[entity-name]]>

## Sources
- [[sources/<slug>]] — <one line on what this source says about the concept>
```

### Step 6: Update the indexes

Under `index_style: per-section`, each of `<wiki_root>/sources/index.md`,
`entities/index.md`, `concepts/index.md` and `<derived_dir>/index.md` opens with a short
description followed by a catalog, and `<wiki_root>/index.md` links to each section.
Under `root-only`, a single `<wiki_root>/index.md` holds every entry, grouped by section.

Either way, append new pages under a `## Pages` heading (create it if missing). Never
overwrite an existing catalog:

```markdown
## Pages
- [[<slug>]] — <one-line description> | added: YYYY-MM-DD
```

### Step 7: Append to the log

Append one entry to `<wiki_root>/log.md` (create the file with a `# Wiki Log` header if
it doesn't exist):

```markdown
## [<YYYY-MM-DD>] ingest | <source title>

- **Source page:** `<wiki_root>/sources/<slug>.md`
- **New concept pages:** <list or "none">
- **New entity pages:** <list or "none">
- **Updated pages:** <list or "none">
```

### Step 8: Run lint

Run the `lint` skill once all pages are written
(`python3 "${CLAUDE_PLUGIN_ROOT}/skills/lint/lint.py"`). Fix any new dangling links or
index drift before finishing. Append the result to `<wiki_root>/log.md` and write the
full report to `<wiki_root>/lint-reports/<YYYY-MM-DD>.md`.

Don't skip this step. One ingest adds several pages and many links, and a dangling
link is cheapest to fix before another contributor's ingest builds on top of it.

---

## After the ingest

Debrief the user in a few short paragraphs covering:

1. What the source is and what it adds to the wiki
2. Which pages were created or updated (a summary, not a full list)
3. Any open questions, gaps or contradictions you noticed
4. Follow-up sources worth ingesting

The user may correct the summary, shift the emphasis or ask follow-up questions. Make
those revisions before finishing.

---

## Quality standards

- **Summaries:** write for a reader who hasn't seen the source. Synthesise instead of
  transcribing, and follow `source_policy` on wording.
- **Concept and entity pages:** update them on every ingest that touches them, even
  when the source is mostly about something else.
- **Cross-references:** link in both directions wherever a reader of either page would
  want the other.
- **Contradictions:** record both claims with their sources; never overwrite silently.

## Version control

Follow `git_workflow` from the schema.

Under `pr`, the wiki lives in a shared repo and each ingest lands as a reviewed branch:

```bash
git checkout -b ingest/<slug>
git add <wiki_root>
git commit -m "ingest: <source title> — added <N> concepts, <M> entities"
git push -u origin ingest/<slug>
```

Then open a PR (check the repo's `CONTRIBUTING.md`). Don't push to the default branch
unless the user explicitly asks.

Under `direct`, commit to the current branch with the same message format and no PR.
Under `none`, leave version control alone; the wiki may not be a git repo at all.
