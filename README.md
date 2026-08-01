# wiki-skills

A Claude Code plugin holding the skills that maintain an agentic personal wiki (the
Karpathy pattern): ingesting sources, linting the graph, querying it, and generating
revision material from it.

The plugin holds logic only. Anything that varies between wikis — directory names, the
domain taxonomy, whether raw source files may be archived — lives in each consuming
repo's `.claude/wiki-schema.md`, which the skills read at run time. Adding a new wiki
should be a schema file plus a plugin install, with no change to this repo.

## Skills

| Skill | Purpose |
|---|---|
| `ingest` | Bring one source into the wiki: acquisition (including transcript capture for recordings), source page, entity/concept pages, index and log updates. Ships `fetch_transcript.py`. |
| `content-digest` | Turn ingested material into a layered digest built to be read instead of the original. Calls `ingest` first when handed new sources. |
| `lint` | Health checks — orphans, dangling links, index drift, frontmatter and domain issues. Ships `lint.py`. |
| `query` | Synthesise an answer across pages with citations, and file valuable output back. |
| `cue-cards` | Generate spaced-repetition decks in Obsidian SR format, with an Anki TSV export. |
| `practice-exam` | Build a practice exam and answer key as typeset PDFs via LaTeX. |

## Install

```bash
/plugin marketplace add bronsonhill/wiki-skills
/plugin install wiki@wiki-skills
```

To pre-register it for everyone working in a given repo, commit this to that repo's
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

A project-local skill of the same name overrides the plugin's copy, which is the escape
hatch when one repo needs to diverge temporarily.

## Configuring a wiki

Copy `wiki-schema.template.md` to `.claude/wiki-schema.md` in the consuming repo and
edit its frontmatter. Those keys — `wiki_root`, `source_policy`, `raw_dir`,
`derived_dir`, `index_style`, `domains`, `subject`, `git_workflow` — are what the skills
read; `lint.py` parses the same frontmatter directly and needs no arguments when run
from anywhere inside the repo. Every key has a default, so a minimal schema is valid.

`source_policy` is the one worth deliberating over. `link-only` means sources are never
copied into the repo, only linked and summarised in original words. Set it wherever the
sources are copyright or the repo is public.

## Consuming repos

- [cmas](https://github.com/bronsonhill/cmas) — single-subject public wiki, `source_policy: link-only`.
- MC-SOFTENG — local multi-domain study wiki, `source_policy: archive-raw`.

## Status

Version 0.3.0 splits acquisition from presentation. `ingest` owns everything that
brings material into the wiki, transcript capture included; `content-digest` (renamed
from `lecture-digest`) owns turning that material into something readable, and calls
`ingest` first when it is handed new sources.

That split is why YouTube is no longer baked into the digest workflow. Transcript
acquisition is an ingest concern, and the YouTube-specific parts of it — URL cleaning,
the caption-overlap dedupe, the mangled-terminology warnings — live in
`ingest/references/youtube.md`, read only when a source is actually on YouTube.
Sources on other hosts, or with a transcript already supplied, never load it.

Transcript destination follows `source_policy`: kept in the wiki under `archive-raw`,
written to a scratch directory outside the repo under `link-only`. A transcript is
closer to the source material than a summary is, so it falls under the same constraint
as the slides.

Digests are written to `<derived_dir>`, not `sources/`. Ingest already writes one source
page per source, and a second one would break the indexes and orphan checks.

Pin consuming repos to a tag rather than tracking the default branch, so a mid-refactor
skill never changes ingest behaviour under someone without warning.
