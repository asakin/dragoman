"""Tests for agent file installation, uninstallation, and CLAUDE.md import management."""

import textwrap
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


# --- CLAUDE.md import line management ---

def test_add_import_creates_claude_md(tmp_path):
    """If CLAUDE.md doesn't exist, add_claude_md_import should create it."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path, status = agent.add_claude_md_import(claude_dir)

    assert status == "created"
    assert md_path.exists()
    content = md_path.read_text()
    assert agent.import_line_for(claude_dir) in content


def test_add_import_idempotent(tmp_path):
    """Adding the import line twice should report 'already-present' the second time."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    agent.add_claude_md_import(claude_dir)
    _, status = agent.add_claude_md_import(claude_dir)

    assert status == "already-present"


def test_add_import_preserves_existing_content(tmp_path):
    """Adding the import should not clobber existing CLAUDE.md content."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Simulate a project-level CLAUDE.md (lives in parent of .claude)
    md_path = claude_dir.parent / "CLAUDE.md"
    existing = "# My project rules\n\nDo not touch production.\n"
    md_path.write_text(existing)

    agent.add_claude_md_import(claude_dir)

    content = md_path.read_text()
    assert "# My project rules" in content
    assert "Do not touch production." in content
    assert agent.import_line_for(claude_dir) in content


def test_remove_import(tmp_path):
    """remove_claude_md_import should remove exactly the import line."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    agent.add_claude_md_import(claude_dir)
    md_path, status = agent.remove_claude_md_import(claude_dir)

    assert status == "removed"
    content = md_path.read_text()
    assert agent.import_line_for(claude_dir) not in content


def test_remove_import_absent(tmp_path):
    """Removing an import that was never added should report 'absent'."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    md_path = claude_dir.parent / "CLAUDE.md"
    md_path.write_text("# Empty\n")

    _, status = agent.remove_claude_md_import(claude_dir)

    assert status == "absent"


def test_remove_import_no_file(tmp_path):
    """Removing when CLAUDE.md doesn't exist should report 'no-file'."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    _, status = agent.remove_claude_md_import(claude_dir)

    assert status == "no-file"
