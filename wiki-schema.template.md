---
title: Wiki Schema
version: 0.2
wiki_root: wiki
source_policy: link-only
raw_dir: sources/raw
derived_dir: materials
index_style: per-section
domains: []
subject: <display name of the subject, or omit for a general-purpose wiki>
git_workflow: none
---

# Wiki Schema

Copy this file to `.claude/wiki-schema.md` in a repo that consumes the `wiki` plugin,
then edit the frontmatter. Every skill in the plugin reads the frontmatter, and
`lint/lint.py` parses it directly. The prose below is for people, and for the agent
when a convention calls for judgement.

## Configuration keys

| Key | Values | Meaning |
|---|---|---|
| `wiki_root` | path | Root directory of the vault, relative to the repo root. |
| `source_policy` | `link-only` \| `archive-raw` | `link-only` records a URL and an original summary and never copies the source into the repo. Use it when sources are under copyright or the repo is public or shared. `archive-raw` also copies the original into `raw_dir`. |
| `raw_dir` | path | Where archived originals live, relative to `wiki_root`. Used only under `archive-raw`. |
| `derived_dir` | dirname | Section for worked examples, syntheses, cue-card decks and other revision material. |
| `index_style` | `per-section` \| `root-only` | `per-section` gives each section its own `index.md` plus a root catalog; `root-only` catalogs everything in one root `index.md`. |
| `domains` | list | Allowed top-level `domain` values. Leave empty for a single-subject wiki; pages then carry no `domain` field and lint skips its domain checks. |
| `subject` | string | Display name, used in page prose, card tags and generated exam papers. |
| `git_workflow` | `pr` \| `direct` \| `none` | How ingests reach version control. Use `none` for a wiki that isn't a git repo. |

## Directory structure

```
<wiki_root>/
├── index.md          # catalog (root-only) or links to each section (per-section)
├── log.md            # append-only chronological history of ingests, lints, queries
├── sources/          # one page per external resource
├── entities/         # people, models, tools, papers, software
├── concepts/         # ideas, mechanisms, algorithms
├── <derived_dir>/    # worked examples, syntheses, revision material
└── lint-reports/     # frozen lint snapshots
```

## Page conventions

- **Naming:** kebab-case.md (e.g. `agent-based-model.md`).
- **Frontmatter (YAML)**, required on every content page:
  ```yaml
  ---
  title: Agent-Based Model
  description: Simulation built from autonomous agents whose interactions produce system-level behaviour
  type: concept | entity | source | material
  domain: academic/cmas    # only when `domains` is non-empty
  tags: [abm, netlogo]
  date: 2026-08-01
  ---
  ```
  `source` pages also carry `link: <url>`. `description` is one line, the same text as
  the page's index entry; site generators such as Quartz show it in page listings and
  link previews.
- **Wikilinks:** `[[page-name]]` for all cross-references, in both directions where
  possible.
- **Citations:** claims on concept, entity and derived pages link back to the
  `[[sources/xxx]]` page they came from.
- **Images:** only original diagrams, or images you have the rights to. Store them under
  `<wiki_root>/<derived_dir>/assets/`.
- **Cue-card decks** have no frontmatter, following the Obsidian Spaced Repetition
  convention. `lint` skips them.

## Schema evolution

Update this file when conventions change. `lint/lint.py` encodes the frontmatter rules,
so change the script in the same commit as the schema. If only the schema changes, lint
keeps checking the old rules and reports nothing wrong.
