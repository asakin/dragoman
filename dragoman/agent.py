"""Agent file installation for Claude Code.

Copies the contents of templates/ into the user's .claude/ directory
so Claude Code picks up the Dragoman sub-agent and its memory.

Layout mirrors .claude/ structure:
    templates/agents/dragoman/         → .claude/agents/dragoman/
    templates/agent-memory/dragoman/   → .claude/agent-memory/dragoman/

Plus the caller-side persona, handled separately:
    templates/dragoman.md              → inlined into CLAUDE.md as a
                                         marker-delimited block (between
                                         <!-- BEGIN DRAGOMAN --> and
                                         <!-- END DRAGOMAN -->). Not copied
                                         as a standalone file — Claude Code's
                                         @import syntax doesn't reliably load
                                         from the harness, so we inline.

Only dragoman's own files are written. Other agents' files are never touched.
Existing dragoman files are overwritten (they're immutable templates).
New files added to the template directories are picked up automatically.
"""

import filecmp
import re
import shutil
from pathlib import Path

# Markers for the inline block in CLAUDE.md.
BLOCK_BEGIN = "<!-- BEGIN DRAGOMAN -->"
BLOCK_END = "<!-- END DRAGOMAN -->"
BLOCK_WARNING = (
    "<!-- Everything in here will be uninstalled if you uninstall Dragoman, "
    "so don't put anything in here. -->"
)

# Source file for the inline block. Lives in templates/, never copied to .claude/.
BLOCK_SOURCE = Path("dragoman.md")

# Pre-v0.7 versions copied this file to .claude/dragoman.md and added an
# @import line to CLAUDE.md. Both are superseded by the inline block.
# Install and uninstall clean these up so upgrades are seamless.
LEGACY_INSTALLED_FILES = [Path("dragoman.md")]
LEGACY_IMPORT_LINE_GLOBAL = "@dragoman.md"
LEGACY_IMPORT_LINE_PROJECT = "@.claude/dragoman.md"


def templates_dir() -> Path:
    """Return the path to the bundled templates directory."""
    return Path(__file__).parent / "templates"


def _discover_files() -> list[Path]:
    """Walk templates/ and return files that get copied to .claude/.

    Excludes the inline-block source and any legacy files that are now
    managed via different means.
    """
    root = templates_dir()
    skip = set(LEGACY_INSTALLED_FILES) | {BLOCK_SOURCE}
    return sorted(
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file()
        and not p.name.startswith(".")
        and p.relative_to(root) not in skip
    )


def install(claude_dir: Path) -> dict[str, str]:
    """Copy all template files into <claude_dir>/.

    Creates subdirectories as needed. Silently cleans up legacy files from
    prior versions if present (e.g., pre-v0.7 ~/.claude/dragoman.md).

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

    # Silent cleanup of legacy files from prior versions.
    for rel_path in LEGACY_INSTALLED_FILES:
        legacy = claude_dir / rel_path
        if legacy.exists():
            legacy.unlink()

    return results


def uninstall(claude_dir: Path) -> dict[str, str]:
    """Remove dragoman's files from <claude_dir>/.

    Cleans up empty dragoman/ directories. Includes legacy files from prior
    versions so an upgrade-then-uninstall is clean.

    Returns a dict of {relative_path: status} where status is one of:
    "removed", "absent", "missing-dir".
    """
    claude_dir = Path(claude_dir)
    results = {}

    manifest = (
        _discover_files()
        + [Path("agent-memory") / "dragoman" / "configured-models.md"]
        + LEGACY_INSTALLED_FILES
    )

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

            # Clean up empty dragoman/ subdirectory.
            parent = target.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()

    return results


# ---------------------------------------------------------------------------
# CLAUDE.md block management
# ---------------------------------------------------------------------------

def _is_global(claude_dir: Path) -> bool:
    return Path(claude_dir).resolve() == (Path.home() / ".claude").resolve()


def claude_md_path(claude_dir: Path) -> Path:
    """Where CLAUDE.md lives for a given install target.

    Global  (~/.claude)       → ~/.claude/CLAUDE.md
    Project (<root>/.claude)  → <root>/CLAUDE.md
    """
    claude_dir = Path(claude_dir)
    if _is_global(claude_dir):
        return claude_dir / "CLAUDE.md"
    return claude_dir.parent / "CLAUDE.md"


def _legacy_import_line(claude_dir: Path) -> str:
    return LEGACY_IMPORT_LINE_GLOBAL if _is_global(claude_dir) else LEGACY_IMPORT_LINE_PROJECT


def _block_content() -> str:
    """Render the marker-delimited block from templates/dragoman.md."""
    body = (templates_dir() / BLOCK_SOURCE).read_text().rstrip("\n")
    return f"{BLOCK_BEGIN}\n{BLOCK_WARNING}\n\n{body}\n\n{BLOCK_END}\n"


_BLOCK_PATTERN = re.compile(
    rf"{re.escape(BLOCK_BEGIN)}.*?{re.escape(BLOCK_END)}\n?",
    flags=re.DOTALL,
)


def _strip_legacy_import(content: str, claude_dir: Path) -> str:
    """Remove the pre-v0.7 @dragoman.md import line if present."""
    legacy = _legacy_import_line(claude_dir)
    lines = content.splitlines(keepends=True)
    new_lines = [l for l in lines if l.strip() != legacy]
    return "".join(new_lines)


def add_claude_md_block(claude_dir: Path) -> tuple[Path, str]:
    """Ensure CLAUDE.md contains the current dragoman block.

    Replaces any existing dragoman block (so template updates propagate on
    re-install). Migrates the pre-v0.7 @dragoman.md import line if present.

    Returns (path, status) where status is one of:
    "created"   — CLAUDE.md didn't exist; we created it with the block.
    "added"     — CLAUDE.md existed without a block; we appended one.
    "updated"   — A stale block or legacy @import line existed; we replaced/migrated.
    "unchanged" — The block was already current; no write happened.
    """
    md_path = claude_md_path(claude_dir)
    block = _block_content()

    if not md_path.exists():
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(block)
        return md_path, "created"

    original = md_path.read_text()
    cleaned = _strip_legacy_import(original, claude_dir)
    had_block = bool(_BLOCK_PATTERN.search(cleaned))

    if had_block:
        new_content = _BLOCK_PATTERN.sub(block.rstrip("\n") + "\n", cleaned, count=1)
    else:
        sep = "" if cleaned.endswith("\n") else "\n"
        new_content = f"{cleaned}{sep}\n{block}"

    if new_content == original:
        return md_path, "unchanged"

    md_path.write_text(new_content)

    if had_block or cleaned != original:
        return md_path, "updated"
    return md_path, "added"


def remove_claude_md_block(claude_dir: Path) -> tuple[Path, str]:
    """Remove the dragoman block from CLAUDE.md.

    Also cleans up any pre-v0.7 @dragoman.md import line.

    Returns (path, status) where status is one of:
    "removed" — block (or legacy line) was present and removed.
    "absent"  — neither block nor legacy line was present.
    "no-file" — CLAUDE.md doesn't exist.
    """
    md_path = claude_md_path(claude_dir)

    if not md_path.exists():
        return md_path, "no-file"

    original = md_path.read_text()
    new_content = _strip_legacy_import(original, claude_dir)
    new_content = _BLOCK_PATTERN.sub("", new_content)

    if new_content == original:
        return md_path, "absent"

    # Tidy trailing whitespace from the block removal.
    new_content = new_content.rstrip() + "\n" if new_content.strip() else ""
    md_path.write_text(new_content)
    return md_path, "removed"
