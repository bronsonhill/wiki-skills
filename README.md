# wiki-skills

A Claude Code plugin with the skills that maintain an agentic personal wiki (the
Karpathy pattern): ingest sources, lint the link graph, query it, and turn it into
revision material.

The plugin holds logic only. Anything that differs between wikis (directory names, the
domain list, whether raw source files may be archived) lives in the consuming repo's
`.claude/wiki-schema.md`, which the skills read at run time. Adding a wiki takes a
schema file and a plugin install; this repo doesn't change.

## Skills

| Skill | Purpose |
|---|---|
| `ingest` | Brings one source into the wiki: gets a transcript for recordings, writes the source page, creates or updates entity and concept pages, and updates the indexes and log. Ships `fetch_transcript.py`. |
| `content-digest` | Builds a layered digest from ingested material, written to be read in place of the original. Runs `ingest` first on any new sources. |
| `lint` | Finds orphans, dangling links, index drift, and frontmatter and domain errors. Ships `lint.py`. |
| `query` | Answers questions from the wiki with citations, and files useful answers back as pages. |
| `cue-cards` | Writes spaced-repetition decks in Obsidian SR format and exports them to Anki TSV. |
| `practice-exam` | Writes a practice exam and answer key in LaTeX and compiles both to PDF. |

## Install

```bash
/plugin marketplace add bronsonhill/wiki-skills
/plugin install wiki@wiki-skills
```

To pre-register it for everyone working in a repo, commit this to that repo's
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "wiki-skills": {
      "source": { "source": "github", "repo": "bronsonhill/wiki-skills" }
    }
  },
  "enabledPlugins": { "wiki@wiki-skills": true }
}
```

A project-local skill with the same name overrides the plugin's copy. Use that when one
repo needs to diverge for a while.

## Configuring a wiki

Copy `wiki-schema.template.md` to `.claude/wiki-schema.md` in the consuming repo and
edit its frontmatter. The skills read eight keys: `wiki_root`, `source_policy`,
`raw_dir`, `derived_dir`, `index_style`, `domains`, `subject` and `git_workflow`.
`lint.py` parses the same frontmatter itself, so it runs without arguments from
anywhere in the repo. Every key has a default; set only the ones that differ.

`source_policy` needs the most thought. Under `link-only`, sources are never copied
into the repo, and pages hold a link plus a summary in original words. Use it whenever
the sources are under copyright or the repo is public.

## Consuming repos

- [cmas](https://github.com/bronsonhill/cmas): single-subject public wiki, `source_policy: link-only`.
- MC-SOFTENG: local multi-domain study wiki, `source_policy: archive-raw`.

## Status

Version 0.3.0 separates acquisition from presentation. `ingest` owns everything that
brings material into the wiki, transcript capture included. `content-digest` (formerly
`lecture-digest`) turns that material into something readable, and calls `ingest` first
when it gets new sources.

YouTube handling moved out of the digest workflow as a result. URL cleaning, the
caption-overlap dedupe and the warnings about mangled terminology now live in
`ingest/references/youtube.md`, which the agent reads only when a source is on YouTube.

Where a transcript goes depends on `source_policy`: into the wiki under `archive-raw`,
into a scratch directory outside the repo under `link-only`. A transcript reproduces
the source almost word for word, so it gets the same treatment as the slides.

Digests go to `<derived_dir>`, not `sources/`. Ingest already writes one source page per
source; a second would break the indexes and the orphan check.

Pin consuming repos to a tag instead of tracking the default branch, so a half-finished
refactor here can't change ingest behaviour for someone without warning.
