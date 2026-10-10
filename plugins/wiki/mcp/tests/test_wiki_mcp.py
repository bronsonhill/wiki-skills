import json
import subprocess
import sys
from pathlib import Path

import pytest

import wiki_mcp

SCRIPT = Path(__file__).resolve().parents[1] / "wiki_mcp.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch):
    """Keep the real ~/.config registry and the cwd's project registry out of every test."""
    monkeypatch.setenv("WIKI_MCP_REGISTRY", str(tmp_path / "user/wikis.json"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "elsewhere"))
    (tmp_path / "elsewhere").mkdir()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "cmas"
    write(repo / ".claude/wiki-schema.md", "---\nwiki_root: notes\n---\n")
    root = repo / "notes"
    write(root / "index.md", "# Root\n- [[concepts/index|Concepts]]\n")
    write(root / "concepts/index.md", "# Concepts\n- [[agent-based-model]]\n")
    write(
        root / "concepts/agent-based-model.md",
        "---\ntitle: Agent-Based Model\ntype: concept\ntags: [abm, netlogo]\n---\n"
        "An ABM simulates individual agents. See [[emergence]].\n",
    )
    write(
        root / "concepts/emergence.md",
        "---\ntitle: Emergence\ntype: concept\ntags: []\n---\n"
        "Macro patterns from micro rules, as in an [[agent-based-model|ABM]].\n",
    )
    write(root / "sources/emergence.md", "---\ntitle: Emergence lecture\ntype: source\n---\nLecture.\n")
    write(root / "lint-reports/2026-01-01.md", "agent-based-model is orphaned\n")
    return repo


@pytest.fixture
def server(repo: Path) -> wiki_mcp.Server:
    return wiki_mcp.Server(wiki_mcp.parse_wikis([f"cmas={repo}"]))


def test_schema_sets_wiki_root(repo: Path):
    assert wiki_mcp.resolve_wiki_root(repo) == (repo / "notes").resolve()
    assert wiki_mcp.resolve_wiki_root(repo / "notes") == (repo / "notes").resolve()


def test_index_root_and_section(server):
    assert "# Root" in server.call("wiki_index", {})
    assert "# Concepts" in server.call("wiki_index", {"section": "concepts"})
    with pytest.raises(wiki_mcp.ToolError, match="sections with an index: concepts"):
        server.call("wiki_index", {"section": "../.."})


def test_search_ranks_title_hits_and_skips_lint_reports(server):
    out = server.call("wiki_search", {"query": "agent model"})
    lines = [l for l in out.splitlines() if l.startswith("- ")]
    assert lines[0].startswith("- concepts/agent-based-model")
    assert "lint-reports" not in out


def test_search_requires_every_term_and_filters_type(server):
    assert "No pages match" in server.call("wiki_search", {"query": "emergence netlogo zebra"})
    out = server.call("wiki_search", {"query": "emergence", "type": "source"})
    assert "sources/emergence" in out and "concepts/emergence" not in out


@pytest.mark.parametrize("ref", ["concepts/agent-based-model", "agent-based-model.md", "[[agent-based-model|ABM]]"])
def test_read_resolves_refs_and_lists_backlinks(server, ref):
    out = server.call("wiki_read", {"page": ref})
    assert out.startswith("page id: concepts/agent-based-model")
    assert "Linked from: concepts/emergence, concepts/index" in out


def test_read_ambiguous_stem(server):
    with pytest.raises(wiki_mcp.ToolError, match="concepts/emergence, sources/emergence"):
        server.call("wiki_read", {"page": "emergence"})


def test_read_rejects_paths_outside_wiki(server):
    with pytest.raises(wiki_mcp.ToolError):
        server.call("wiki_read", {"page": "../.claude/wiki-schema"})


def test_multiple_wikis_need_a_name(repo: Path):
    s = wiki_mcp.Server(wiki_mcp.parse_wikis([f"a={repo}", f"b={repo}"]))
    with pytest.raises(wiki_mcp.ToolError, match="pass `wiki`"):
        s.call("wiki_index", {})
    assert "# Root" in s.call("wiki_index", {"wiki": "b"})


def test_stdio_round_trip(repo: Path):
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "wiki_read", "arguments": {"page": "nope"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "bogus"},
    ]
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--wiki", f"cmas={repo}"],
        input="".join(json.dumps(r) + "\n" for r in requests),
        capture_output=True, text=True, timeout=10, check=True,
    )
    replies = [json.loads(l) for l in proc.stdout.splitlines()]
    assert [r["id"] for r in replies] == [1, 2, 3, 4]
    assert replies[0]["result"]["protocolVersion"] == "2025-06-18"
    assert {t["name"] for t in replies[1]["result"]["tools"]} == {"wiki_index", "wiki_search", "wiki_read"}
    assert replies[2]["result"]["isError"] is True
    assert replies[3]["error"]["code"] == -32601


def test_no_wikis_points_at_connect():
    with pytest.raises(wiki_mcp.ToolError, match="/wiki:connect"):
        wiki_mcp.Server().call("wiki_index", {})


def test_add_is_picked_up_without_restart(repo: Path, tmp_path: Path, capsys):
    server = wiki_mcp.Server()
    assert wiki_mcp.main(["add", "cmas", str(repo)]) == 0
    assert "added cmas" in capsys.readouterr().out
    assert "# Root" in server.call("wiki_index", {})
    assert wiki_mcp.main(["remove", "cmas"]) == 0
    with pytest.raises(wiki_mcp.ToolError, match="/wiki:connect"):
        server.call("wiki_index", {})


def test_add_rejects_non_wiki(tmp_path: Path, capsys):
    assert wiki_mcp.main(["add", "x", str(tmp_path / "elsewhere")]) == 1
    assert "no index.md" in capsys.readouterr().err
    assert not (tmp_path / "user/wikis.json").exists()


def test_project_registry_overrides_user(repo: Path, tmp_path: Path):
    other = tmp_path / "other"
    write(other / "index.md", "# Other\n")
    assert wiki_mcp.main(["add", "w", str(repo)]) == 0
    assert wiki_mcp.main(["add", "w", str(other), "--project", str(tmp_path / "elsewhere")]) == 0
    # A session in a subdirectory of the project still finds the project registry.
    sub = tmp_path / "elsewhere/src"
    sub.mkdir()
    assert "# Other" in wiki_mcp.Server(project_dir=sub).call("wiki_index", {})
    assert "# Root" in wiki_mcp.Server(project_dir=tmp_path).call("wiki_index", {})


def test_moved_wiki_reports_missing_path(repo: Path, tmp_path: Path):
    assert wiki_mcp.main(["add", "cmas", str(repo)]) == 0
    repo.rename(tmp_path / "moved")
    with pytest.raises(wiki_mcp.ToolError, match="no longer exists"):
        wiki_mcp.Server().call("wiki_index", {})
