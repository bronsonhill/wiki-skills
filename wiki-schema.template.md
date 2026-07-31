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
then edit the frontmatter. The frontmatter is the machine-readable half — every skill
in the plugin reads it, and `wiki_lint/lint.py` parses it directly. The prose below is
for humans and for the agent's judgement calls.

## Configuration keys

| Key | Values | Meaning |
|---|---|---|
| `wiki_root` | path | Root directory of the vault, relative to the repo root. |
| `source_policy` | `link-only` \| `archive-raw` | `link-only` records a URL and an original summary and never copies the source into the repo. Use it when sources are copyright or the repo is public or shared. `archive-raw` also copies the original into `raw_dir`. |
| `raw_dir` | path | Where archived originals live, relative to `wiki_root`. Only meaningful under `archive-raw`. |
| `derived_dir` | dirname | Section holding worked examples, syntheses, cue-card decks, and revision material. |
| `index_style` | `per-section` \| `root-only` | Whether each section keeps its own `index.md` alongside a root catalog, or everything is cataloged in one root `index.md`. |
| `domains` | list | Allowed top-level `domain` values. Leave empty for a single-subject wiki, in which case pages carry no `domain` field and the lint's domain checks are skipped. |
| `subject` | string | Display name, used in page prose, card tags, and generated exam papers. |
| `git_workflow` | `pr` \| `direct` \| `none` | How ingests reach version control. `none` for a wiki that isn't a git repo. |

## Directory structure

```
<wiki_root>/
├── index.md          # catalog (root-only) or links to each section (per-section)
├── log.md            # append-only chronological history of ingests, lints, queries
├── sources/          # one page per external resource
├── entities/         # people, models, tools, papers, software
├── concepts/         # ideas, mechanisms, algorithms
├── <derived_dir>/    # worked examples, syntheses, revision material
└── lint-reports/     # frozen wiki_lint snapshots
```

## Page conventions

- **Naming:** kebab-case.md (e.g. `agent-based-model.md`).
- **Frontmatter (YAML)**, required on every content page:
  ```yaml
  ---
  title: Agent-Based Model
  type: concept | entity | source | material
  domain: academic/cmas    # only when `domains` is non-empty
  tags: [abm, netlogo]
  date: 2026-08-01
  ---
  ```
  `source` pages also carry `link: <url>`.
- **Wikilinks:** `[[page-name]]` for all cross-references, bidirectional where possible.
- **Citations:** claims on concept, entity, and derived pages should link back to the
  `[[sources/xxx]]` page they came from.
- **Images:** only original diagrams or images you have rights to use. Store under
  `<wiki_root>/<derived_dir>/assets/`.
- **Cue-card decks** intentionally omit frontmatter, following the Obsidian Spaced
  Repetition convention. `wiki_lint` exempts them.

## Schema evolution

Update this file when conventions change. A schema change that implies a script change
should land alongside it — `wiki_lint/lint.py` encodes the frontmatter rules, so a
schema edit without a matching script edit is silent.
