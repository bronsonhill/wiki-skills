# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.
- Python scripts under a skill's `scripts/` dir get their own scoped `tests/` and
  `pytest.ini` next to the skill (e.g. `plugins/wiki/skills/cue-cards/tests/`), not a
  repo-wide test suite. Use a venv (`python3 -m venv .venv && source .venv/bin/activate
  && pip install pytest`) to run them; `.venv/` is gitignored.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
