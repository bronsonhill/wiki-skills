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

## Consuming repos

- [cmas](https://github.com/bronsonhill/cmas) — single-subject public wiki, `source_policy: link-only`.
- MC-SOFTENG — local multi-domain study wiki, `source_policy: archive-raw`.

## Status

Version 0.1.0 is cmas's skills lifted unchanged, to prove out distribution before any
merge work. Two things are known to be still repo-specific and are the next work:

1. **Script paths.** `practice-exam/SKILL.md` and `cue-cards/SKILL.md` invoke their
   helper scripts via `.claude/skills/<name>/…`, which is where the skills used to live.
   Under a plugin install they need `${CLAUDE_PLUGIN_ROOT}` instead.
2. **Hard-coded conventions.** The skills assume `materials/`, per-section indexes, and
   link-only sourcing. These need to move into `wiki-schema.md` before MC-SOFTENG can
   use the plugin.

Pin consuming repos to a tag rather than tracking the default branch, so a mid-refactor
skill never changes ingest behaviour under someone without warning.
