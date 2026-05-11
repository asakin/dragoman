"""Agent file installation for Claude Code.

Copies the contents of templates/ into the user's .claude/ directory
so Claude Code picks up the Dragoman sub-agent and its memory.

Layout mirrors .claude/ structure:
    templates/agents/dragoman/      → .claude/agents/dragoman/
    templates/agent-memory/dragoman/ → .claude/agent-memory/dragoman/

Only dragoman's own files are written. Other agents' files are never touched.
Existing dragoman files are overwritten (they're immutable templates).
New files added to the template directories are picked up automatically.
"""

import filecmp
import shutil
from pathlib import Path


def templates_dir() -> Path:
    """Return the path to the bundled templates directory."""
    return Path(__file__).parent / "templates"


def _discover_files() -> list[Path]:
    """Walk the templates directory and return all files as relative paths."""
    root = templates_dir()
    return sorted(
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )


def install(claude_dir: Path) -> dict[str, str]:
    """Copy all template files into <claude_dir>/.

    Creates subdirectories as needed. Only overwrites dragoman's own files
    (files that exist in the templates directory).

    Returns a dict of {relative_path: status} where status is one of:
    "created", "updated", "unchanged".
    """
    claude_dir = Path(claude_dir)
    src_root = templates_dir()
    results = {}

    for rel_path in _discover_files():
        src = src_root / rel_path
        dst = claude_dir / rel_path

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            if filecmp.cmp(src, dst, shallow=False):
                results[str(rel_path)] = "unchanged"
            else:
                shutil.copy2(src, dst)
                results[str(rel_path)] = "updated"
        else:
            shutil.copy2(src, dst)
            results[str(rel_path)] = "created"

    return results


def uninstall(claude_dir: Path) -> dict[str, str]:
    """Remove dragoman's files from <claude_dir>/.

    Only removes files that match the current template manifest.
    Cleans up empty dragoman/ directories but leaves parent dirs intact.

    Returns a dict of {relative_path: status} where status is one of:
    "removed", "absent", "missing-dir".
    """
    claude_dir = Path(claude_dir)
    results = {}

    # Add configured-models.md which is generated dynamically, not from templates
    manifest = _discover_files() + [Path("agent-memory") / "dragoman" / "configured-models.md"]

    if not claude_dir.exists():
        for rel_path in manifest:
            results[str(rel_path)] = "missing-dir"
        return results

    for rel_path in manifest:
        target = claude_dir / rel_path

        if not target.exists():
            results[str(rel_path)] = "absent"
        else:
            target.unlink()
            results[str(rel_path)] = "removed"

            # Clean up empty dragoman/ subdirectory
            parent = target.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()

    return results
