"""Tests for agent file installation, uninstallation, and CLAUDE.md block management."""

from pathlib import Path

from dragoman import agent


def test_install_creates_files(tmp_path):
    """Install should copy all template files into the target directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    results = agent.install(claude_dir)

    assert len(results) > 0
    for rel_path, status in results.items():
        assert status in ("created", "updated", "unchanged")
        assert (claude_dir / rel_path).exists()


def test_install_idempotent(tmp_path):
    """Running install twice should report 'unchanged' on second pass."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    agent.install(claude_dir)
    results = agent.install(claude_dir)

    for rel_path, status in results.items():
        assert status == "unchanged"


def test_install_does_not_copy_block_source(tmp_path):
    """Install should NOT copy templates/dragoman.md to .claude/dragoman.md.

    That file is inlined into CLAUDE.md as a block instead.
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    agent.install(claude_dir)

    assert not (claude_dir / "dragoman.md").exists()


def test_install_cleans_up_legacy_persona_file(tmp_path):
    """Install should silently remove pre-v0.7 ~/.claude/dragoman.md if present."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    legacy = claude_dir / "dragoman.md"
    legacy.write_text("# Old persona file from v0.6\n")

    agent.install(claude_dir)

    assert not legacy.exists()


def test_uninstall_removes_installed_files(tmp_path):
    """Uninstall should remove exactly what install created."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    installed = agent.install(claude_dir)
    results = agent.uninstall(claude_dir)

    for rel_path in installed:
        assert results[rel_path] == "removed"
        assert not (claude_dir / rel_path).exists()


def test_uninstall_absent_is_safe(tmp_path):
    """Uninstall on a dir that was never installed to should not crash."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    results = agent.uninstall(claude_dir)

    for rel_path, status in results.items():
        assert status in ("absent", "missing-dir")


def test_uninstall_missing_dir(tmp_path):
    """Uninstall on a dir that doesn't exist should report missing-dir."""
    claude_dir = tmp_path / ".claude-does-not-exist"

    results = agent.uninstall(claude_dir)

    for rel_path, status in results.items():
        assert status == "missing-dir"


def test_uninstall_removes_legacy_persona_file(tmp_path):
    """Uninstall should remove pre-v0.7 ~/.claude/dragoman.md if present."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    legacy = claude_dir / "dragoman.md"
    legacy.write_text("# Old persona file from v0.6\n")

    results = agent.uninstall(claude_dir)

    assert not legacy.exists()
    assert results["dragoman.md"] == "removed"


# --- CLAUDE.md block management ---

def test_add_block_creates_claude_md(tmp_path):
    """If CLAUDE.md doesn't exist, add_claude_md_block should create it."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path, status = agent.add_claude_md_block(claude_dir)

    assert status == "created"
    assert md_path.exists()
    content = md_path.read_text()
    assert agent.BLOCK_BEGIN in content
    assert agent.BLOCK_END in content


def test_add_block_appends_to_existing(tmp_path):
    """Add should append a block to an existing CLAUDE.md, preserving content."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = agent.claude_md_path(claude_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# My project rules\n\nDo not touch production.\n")

    _, status = agent.add_claude_md_block(claude_dir)

    assert status == "added"
    content = md_path.read_text()
    assert "# My project rules" in content
    assert "Do not touch production." in content
    assert agent.BLOCK_BEGIN in content


def test_add_block_idempotent(tmp_path):
    """Adding the block twice with the same content should be 'unchanged' the second time."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    agent.add_claude_md_block(claude_dir)
    _, status = agent.add_claude_md_block(claude_dir)

    assert status == "unchanged"


def test_add_block_replaces_stale_block(tmp_path):
    """A stale block in CLAUDE.md should be replaced, not duplicated."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = agent.claude_md_path(claude_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    stale = f"# Header\n\n{agent.BLOCK_BEGIN}\nold dragoman content\n{agent.BLOCK_END}\n"
    md_path.write_text(stale)

    _, status = agent.add_claude_md_block(claude_dir)

    assert status == "updated"
    content = md_path.read_text()
    assert "old dragoman content" not in content
    assert "# Header" in content
    # Only one block should be present.
    assert content.count(agent.BLOCK_BEGIN) == 1
    assert content.count(agent.BLOCK_END) == 1


def test_add_block_migrates_legacy_import_line(tmp_path):
    """Pre-v0.7 @dragoman.md import line should be removed when block is added."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = agent.claude_md_path(claude_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    # Project-level claude_dir uses @.claude/dragoman.md
    legacy_line = agent._legacy_import_line(claude_dir)
    md_path.write_text(f"# My rules\n\n{legacy_line}\n")

    _, status = agent.add_claude_md_block(claude_dir)

    assert status == "updated"
    content = md_path.read_text()
    assert legacy_line not in content
    assert agent.BLOCK_BEGIN in content
    assert "# My rules" in content


def test_remove_block(tmp_path):
    """remove_claude_md_block should remove exactly the block, preserving the rest."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = agent.claude_md_path(claude_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# My project rules\n\nDo not touch production.\n")

    agent.add_claude_md_block(claude_dir)
    _, status = agent.remove_claude_md_block(claude_dir)

    assert status == "removed"
    content = md_path.read_text()
    assert agent.BLOCK_BEGIN not in content
    assert agent.BLOCK_END not in content
    assert "# My project rules" in content
    assert "Do not touch production." in content


def test_remove_block_absent(tmp_path):
    """Removing a block that was never added should report 'absent'."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = agent.claude_md_path(claude_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# Empty\n")

    _, status = agent.remove_claude_md_block(claude_dir)

    assert status == "absent"


def test_remove_block_no_file(tmp_path):
    """Removing when CLAUDE.md doesn't exist should report 'no-file'."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    _, status = agent.remove_claude_md_block(claude_dir)

    assert status == "no-file"


def test_remove_block_also_cleans_legacy_import_line(tmp_path):
    """If only a pre-v0.7 @import line exists, remove should clean it up."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = agent.claude_md_path(claude_dir)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_line = agent._legacy_import_line(claude_dir)
    md_path.write_text(f"# My rules\n\n{legacy_line}\n")

    _, status = agent.remove_claude_md_block(claude_dir)

    assert status == "removed"
    content = md_path.read_text()
    assert legacy_line not in content
    assert "# My rules" in content
