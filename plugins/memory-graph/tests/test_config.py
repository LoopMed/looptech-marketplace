from pathlib import Path

import pytest

from memory_graph.config import find_vault, is_vault, resolve_db_path, resolve_memory_dir


def _project(tmp_path, name="proj"):
    d = tmp_path / name
    d.mkdir()
    return d


def _vault(parent, name="ProjMemory"):
    v = parent / name
    (v / ".obsidian").mkdir(parents=True)
    return v


def test_is_vault_requires_obsidian_config_dir(tmp_path):
    plain = _project(tmp_path, "plain")
    assert not is_vault(plain)
    (plain / ".obsidian").mkdir()
    assert is_vault(plain)


def test_find_vault_detects_subdirectory_vault(tmp_path):
    project = _project(tmp_path)
    vault = _vault(project)
    assert find_vault(str(project)) == vault


def test_find_vault_detects_project_root_as_vault(tmp_path):
    project = _project(tmp_path)
    (project / ".obsidian").mkdir()
    assert find_vault(str(project)) == project


def test_find_vault_prefers_memory_named_vault_and_is_deterministic(tmp_path):
    """Several vaults: the memory-named one wins, not filesystem order."""
    project = _project(tmp_path)
    _vault(project, "aaa-notes")
    expected = _vault(project, "ProjMemory")
    assert find_vault(str(project)) == expected


def test_find_vault_skips_dependency_and_hidden_dirs(tmp_path):
    project = _project(tmp_path)
    _vault(project, "node_modules")
    _vault(project, ".cache")
    assert find_vault(str(project)) is None


def test_find_vault_on_missing_directory_returns_none(tmp_path):
    assert find_vault(str(tmp_path / "does-not-exist")) is None


def test_resolve_memory_dir_autodetects_the_obsidian_vault(tmp_path, monkeypatch):
    project = _project(tmp_path)
    vault = _vault(project)

    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert resolve_memory_dir() == str(vault)


def test_resolve_memory_dir_vault_wins_over_legacy_slug_dir(tmp_path, monkeypatch):
    """A project with both layouts resolves to the vault, not the legacy dir."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    project = _project(tmp_path)
    vault = _vault(project)
    legacy = fake_home / ".claude" / "projects" / str(project).replace("/", "-") / "memory"
    legacy.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert resolve_memory_dir() == str(vault)


def test_resolve_memory_dir_falls_back_to_legacy_slug_dir(tmp_path, monkeypatch):
    """No vault yet (pre-migration install): a legacy dir with notes still resolves."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    project = _project(tmp_path)
    legacy = fake_home / ".claude" / "projects" / str(project).replace("/", "-") / "memory"
    legacy.mkdir(parents=True)
    (legacy / "note.md").write_text("# leftover\n")

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert resolve_memory_dir() == str(legacy)


def test_resolve_memory_dir_ignores_empty_legacy_dir(tmp_path, monkeypatch):
    """Empty harness leftover at ~/.claude/projects/<slug>/memory is not a vault."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    project = _project(tmp_path)
    legacy = fake_home / ".claude" / "projects" / str(project).replace("/", "-") / "memory"
    legacy.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert resolve_memory_dir(required=False) is None


def test_resolve_memory_dir_ignores_unexpanded_placeholder(tmp_path, monkeypatch):
    """Hosts that inject the literal ${MEMORY_GRAPH_DIR} must fall through to auto-detect."""
    project = _project(tmp_path)
    vault = _vault(project)

    monkeypatch.setenv("MEMORY_GRAPH_DIR", "${MEMORY_GRAPH_DIR}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert resolve_memory_dir() == str(vault)


def test_resolve_memory_dir_walks_ancestors_to_find_vault(tmp_path, monkeypatch):
    """cwd like <holding>/IT/App: vault lives two levels up as a sibling of IT."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    holding = fake_home / "holding"
    project = holding / "IT" / "App"
    project.mkdir(parents=True)
    vault = _vault(holding, "CompanyMemory")

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert resolve_memory_dir() == str(vault)


def test_resolve_memory_dir_reads_memory_path_from_claude_md(tmp_path, monkeypatch):
    """memory.path is resolved relative to the file, not the process cwd."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    holding = fake_home / "holding"
    project = holding / "IT" / "App"
    project.mkdir(parents=True)
    declared = holding / "TeamVault"
    declared.mkdir()
    (project / "CLAUDE.md").write_text(
        "```yaml\n"
        "memory:\n"
        "  vault: TeamVault\n"
        "  path: ../../TeamVault   # relativo ao arquivo que declara\n"
        "  pii: permitida\n"
        "```\n"
    )

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    assert Path(resolve_memory_dir()).resolve() == declared.resolve()


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
        fake_home / ".looptech" / "memory-graph" / "-Users-x-projects-Demo" / "index.db"
    )
    assert "/memory/" not in db_path  # lives outside the memory dir, per spec


def test_resolve_db_path_keeps_existing_claude_index(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    legacy = (
        fake_home / ".claude" / "projects" / "-Users-x-projects-Demo"
        / ".memory-graph" / "index.db"
    )
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"")

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("MEMORY_GRAPH_DB", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/Users/x/projects/Demo")

    assert resolve_db_path() == str(legacy)


def test_resolve_db_path_ignores_unexpanded_placeholder(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("MEMORY_GRAPH_DB", "${MEMORY_GRAPH_DB}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/Users/x/projects/Demo")

    assert resolve_db_path() == str(
        fake_home / ".looptech" / "memory-graph" / "-Users-x-projects-Demo" / "index.db"
    )


def test_resolve_db_path_explicit_wins(tmp_path):
    explicit = str(tmp_path / "custom.db")
    assert resolve_db_path(explicit) == explicit
