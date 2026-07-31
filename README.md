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
| `lecture-digest` | Turn lecture videos plus slides into a layered digest that replaces watching, then hand off to `wiki_ingest`. Ships `fetch_transcript.py`. |
| `wiki_ingest` | Add one source to the wiki: source page, entity/concept pages, index and log updates. |
| `wiki_lint` | Health checks — orphans, dangling links, index drift, frontmatter and domain issues. Ships `lint.py`. |
| `wiki_query` | Synthesise an answer across pages with citations, and file valuable output back. |
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

Version 0.2.0 adds `lecture-digest`. Versions before it established the plugin and
parameterised the original five skills against `.claude/wiki-schema.md`, so both wikis'
conventions are reachable through configuration and neither needs a forked copy.

`lecture-digest` branches on `source_policy`: under `archive-raw` it keeps fetched
transcripts in the wiki as archived source material, and under `link-only` it fetches
them to a scratch directory outside the repo and never commits them. A lecture
transcript is closer to the source material than a summary is, so it falls under the
same constraint as the slides.

Pin consuming repos to a tag rather than tracking the default branch, so a mid-refactor
skill never changes ingest behaviour under someone without warning.
