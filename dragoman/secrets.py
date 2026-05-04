"""Resolve API keys from references — 1Password, Keychain, env, or literal.

Keys live where you already keep secrets. Dragoman just knows the lookup path.
When a request needs a key, we resolve once, use it for one HTTPS call, and
discard the value. The literal key never lands on disk in dragoman's process
and never enters the calling agent's context.

Supported reference shapes:
    op://vault/item/field         -> 1Password CLI (`op read`)
    keychain://service/account    -> macOS Keychain (`security find-generic-password -w`)
    env:VAR_NAME                  -> os.environ[VAR_NAME]
    <anything else>               -> returned as-is (treated as a literal key)
"""

import os
import shutil
import subprocess
from typing import Optional


def resolve(reference: Optional[str]) -> Optional[str]:
    """Resolve a reference (or literal) to a key value, or None if empty."""
    if not reference:
        return None
    if reference.startswith("op://"):
        return _resolve_op(reference)
    if reference.startswith("keychain://"):
        return _resolve_keychain(reference)
    if reference.startswith("env:"):
        return os.environ.get(reference[len("env:"):]) or None
    return reference


def _resolve_op(reference: str) -> Optional[str]:
    if not shutil.which("op"):
        raise RuntimeError(
            f"op CLI not found on PATH; install 1Password CLI to use {reference!r}"
        )
    try:
        result = subprocess.run(
            ["op", "read", reference],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"op read {reference!r} timed out after 10s")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if "not currently signed in" in stderr.lower() or "session expired" in stderr.lower():
            raise RuntimeError(
                f"1Password CLI not signed in; run `op signin` first "
                f"(while resolving {reference!r})"
            )
        raise RuntimeError(
            f"op read {reference!r} failed: {stderr or 'no stderr'}"
        )
    return (result.stdout or "").strip() or None


def _resolve_keychain(reference: str) -> Optional[str]:
    rest = reference[len("keychain://"):]
    if "/" not in rest:
        raise RuntimeError(
            f"keychain reference must be keychain://service/account; got {reference!r}"
        )
    service, account = rest.split("/", 1)
    if not shutil.which("security"):
        raise RuntimeError(
            f"`security` CLI not found (macOS Keychain unavailable for {reference!r})"
        )
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"security find-generic-password timed out for {reference!r}")
    if result.returncode != 0:
        raise RuntimeError(
            f"keychain lookup for {reference!r} failed; "
            f"add it with `security add-generic-password -s {service} -a {account} -w <key>`"
        )
    return (result.stdout or "").strip() or None
