from pathlib import Path

import pytest

from memory_graph.config import resolve_db_path, resolve_memory_dir


def test_resolve_memory_dir_uses_project_slug_algorithm(tmp_path, monkeypatch):
    """~/.claude/projects/<slug>/memory, slug = abs project path with / -> -."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    project_dir = "/Users/lclpedro/projects/LoopMed"
    memory_dir = (
        fake_home / ".claude" / "projects" / "-Users-lclpedro-projects-LoopMed" / "memory"
    )
    memory_dir.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", project_dir)

    assert resolve_memory_dir() == str(memory_dir)


def test_resolve_memory_dir_prefers_explicit_env_over_autodetect(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    override = tmp_path / "override-memory"
    override.mkdir()
    # Auto-detect candidate also exists, to prove the env var wins.
    autodetected = (
        fake_home / ".claude" / "projects" / "-some-project" / "memory"
    )
    autodetected.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("MEMORY_GRAPH_DIR", str(override))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/project")

    assert resolve_memory_dir() == str(override)


def test_resolve_memory_dir_explicit_missing_raises_clear_error(tmp_path):
    missing = str(tmp_path / "does-not-exist")
    with pytest.raises(FileNotFoundError, match="memory directory not found"):
        resolve_memory_dir(missing)


def test_resolve_memory_dir_env_set_but_missing_raises_clear_error(tmp_path, monkeypatch):
    missing = str(tmp_path / "does-not-exist")
    monkeypatch.setenv("MEMORY_GRAPH_DIR", missing)
    with pytest.raises(FileNotFoundError, match="MEMORY_GRAPH_DIR"):
        resolve_memory_dir()


def test_resolve_memory_dir_unresolvable_required_raises_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "no-such-project"))

    with pytest.raises(FileNotFoundError, match="MEMORY_GRAPH_DIR"):
        resolve_memory_dir()


def test_resolve_memory_dir_unresolvable_soft_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "no-such-project"))

    assert resolve_memory_dir(required=False) is None


def test_resolve_db_path_is_project_scoped_and_outside_memory_dir(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DB", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/Users/x/projects/Demo")

    db_path = resolve_db_path()

    assert db_path == str(
        fake_home / ".claude" / "projects" / "-Users-x-projects-Demo" / ".memory-graph" / "index.db"
    )
    assert "/memory/" not in db_path  # lives outside the memory dir, per spec


def test_resolve_db_path_explicit_wins(tmp_path):
    explicit = str(tmp_path / "custom.db")
    assert resolve_db_path(explicit) == explicit
