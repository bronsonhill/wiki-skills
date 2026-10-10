---
name: connect
description: >
  Make a wiki built with this plugin queryable from any directory, by registering it
  with the plugin's read-only `wiki` MCP server. Use when the user wants to "connect",
  "hook up", "register" or "add" a wiki, wants to query a wiki from another repo or
  project, asks why the wiki tools aren't available here, or wants to list, rename or
  remove connected wikis.
---

# Wiki Connect

The plugin ships an MCP server (`mcp/wiki_mcp.py`, declared in the plugin's
`.mcp.json`) that starts in every session where the plugin is enabled. It gives the
agent three read-only tools: `wiki_index`, `wiki_search` and `wiki_read`, named
`mcp__plugin_wiki_wiki__*` in Claude Code. The server serves whatever wikis are listed
in its registries, which it re-reads on every call:

- `~/.config/wiki-skills/wikis.json`: available in every session. The default.
- `<project>/.claude/wikis.json`: only in sessions under that project. It wins on a name clash.

Connecting a wiki means adding one entry to a registry. Use the script for that; don't
edit the JSON by hand, because `add` checks that the path holds a wiki first.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/mcp/wiki_mcp.py" add <name> <path> [--project <dir>]
python3 "${CLAUDE_PLUGIN_ROOT}/mcp/wiki_mcp.py" remove <name> [--project <dir>]
python3 "${CLAUDE_PLUGIN_ROOT}/mcp/wiki_mcp.py" list [--project <dir>]
```

## Instructions

### 1. Find the wiki

Use the first of these that gives an answer:

- A path or repo the user named.
- The current repo, if it has `.claude/wiki-schema.md`. The user is probably inside
  the wiki and wants it available elsewhere.
- A search for consuming repos:
  `find ~ -maxdepth 4 -path '*/.claude/wiki-schema.md' -not -path '*/node_modules/*' -not -path '*/Library/*' 2>/dev/null`.
  If it finds one wiki, propose it. If it finds several, ask which ones, or all. If it
  finds none, ask for the path.

Pass the repo root, not the wiki directory. The server reads `wiki_root` from the
schema, so the registration still works if `wiki_root` changes later.

### 2. Pick a name and scope

- **Name:** short and kebab-case, taken from the repo directory (`cmas`, `mc-softeng`).
  The agent passes it as the tools' `wiki` argument when several wikis are registered,
  so keep it short enough to type.
- **Scope:** default to the user registry, which makes the wiki available everywhere.
  Use `--project <dir>` only when the user wants the wiki available in one project and
  nowhere else. A project registry stores `~/`-relative paths, so committing it only
  makes sense in the user's own repos.

Run `list` first. If the name is already registered for a different path, tell the user
before `add` overwrites it.

### 3. Register and check

1. Run `add`. It prints the resolved wiki root and the page count; quote both to the
   user. If it exits 1, the path holds no wiki (no `index.md` under `wiki_root`): ask
   again instead of guessing.
2. If `mcp__plugin_wiki_wiki__wiki_index` is available in this session, call it with
   the new name. The server re-reads the registry on each call, so a wiki added this
   session works right away.
3. If those tools are missing, the session started before the plugin had the server:
   the plugin is older than 0.5.0, or it was updated mid-session. Tell the user to run
   `/plugin update wiki@wiki-skills` if needed, then restart the session. Nothing
   needs re-registering afterwards.

### 4. Make sure the plugin loads everywhere

The server runs only where the plugin is enabled. If `wiki@wiki-skills` is enabled only
in a project's `.claude/settings.json` (often the wiki repo itself), other directories
never start the server. Check `~/.claude/settings.json` for
`"enabledPlugins": {"wiki@wiki-skills": true}`. If it's missing, tell the user to run
`/plugin install wiki@wiki-skills` and choose user scope. Don't edit the settings file
yourself.

### 5. Report

Tell the user, in a line or two, which wikis are connected, at what scope, and how to
use them: ask questions in any session, and the agent will call the wiki tools. To
disconnect, run `/wiki:connect` again and ask for removal.

## Notes

- The server is read-only. Filing an answer back as a page is the `query` skill's job,
  run inside the wiki's repo.
- A moved repo makes the tools return "no longer exists". Fix it by running `add` again
  with the same name and the new path.
- Outside Claude Code, any MCP client can launch the server directly:
  `python3 <plugin>/mcp/wiki_mcp.py [--wiki name=path]`. It reads the same user registry.
