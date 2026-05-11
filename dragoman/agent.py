"""Agent file installation for Claude Code.

Copies the contents of templates/ into the user's .claude/ directory
so Claude Code picks up the Dragoman sub-agent and its memory.

Layout mirrors .claude/ structure:
    templates/agents/dragoman/      → .claude/agents/dragoman/
    templates/agent-memory/dragoman/ → .claude/agent-memory/dragoman/
    templates/dragoman.md           → .claude/dragoman.md  (persona snippet)

Only dragoman's own files are written. Other agents' files are never touched.
Existing dragoman files are overwritten (they're immutable templates).
New files added to the template directories are picked up automatically.

The persona snippet at .claude/dragoman.md is the *main-loop* counterpart to
the agent file — it tells Claude when to invoke Dragoman without proposing,
and how to speak on his behalf. It loads via an @import line added to
CLAUDE.md (see add_claude_md_import below).
"""

import filecmp
import shutil
from pathlib import Path

IMPORT_LINE_GLOBAL = "@dragoman.md"
IMPORT_LINE_PROJECT = "@.claude/dragoman.md"


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


# ---------------------------------------------------------------------------
# CLAUDE.md @import line management
# ---------------------------------------------------------------------------

def _is_global(claude_dir: Path) -> bool:
    return Path(claude_dir).resolve() == (Path.home() / ".claude").resolve()


def claude_md_path(claude_dir: Path) -> Path:
    """Where CLAUDE.md lives for a given install target.

    Global  (~/.claude)      → ~/.claude/CLAUDE.md
    Project (<root>/.claude) → <root>/CLAUDE.md
    """
    claude_dir = Path(claude_dir)
    if _is_global(claude_dir):
        return claude_dir / "CLAUDE.md"
    return claude_dir.parent / "CLAUDE.md"


def import_line_for(claude_dir: Path) -> str:
    """The @import line that loads dragoman.md from this CLAUDE.md."""
    return IMPORT_LINE_GLOBAL if _is_global(claude_dir) else IMPORT_LINE_PROJECT


def add_claude_md_import(claude_dir: Path) -> tuple[Path, str]:
    """Ensure CLAUDE.md contains the dragoman @import line.

    Returns (path, status) where status is "created", "added", or "already-present".
    """
    md_path = claude_md_path(claude_dir)
    line = import_line_for(claude_dir)

    if not md_path.exists():
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(f"{line}\n")
        return md_path, "created"

    content = md_path.read_text()
    if any(l.strip() == line for l in content.splitlines()):
        return md_path, "already-present"

    sep = "" if content.endswith("\n") else "\n"
    md_path.write_text(f"{content}{sep}\n{line}\n")
    return md_path, "added"


def remove_claude_md_import(claude_dir: Path) -> tuple[Path, str]:
    """Remove the dragoman @import line from CLAUDE.md if present.

    Returns (path, status) where status is "removed", "absent", or "no-file".
    Leaves CLAUDE.md in place even if removing the line empties it — the user
    may want to keep the file for other future edits.
    """
    md_path = claude_md_path(claude_dir)
    line = import_line_for(claude_dir)

    if not md_path.exists():
        return md_path, "no-file"

    lines = md_path.read_text().splitlines(keepends=True)
    new_lines = [l for l in lines if l.strip() != line]

    if len(new_lines) == len(lines):
        return md_path, "absent"

    md_path.write_text("".join(new_lines))
    return md_path, "removed"
