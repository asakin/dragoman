import os
import pytest
from dragoman import secrets

def test_resolve_empty():
    assert secrets.resolve(None) is None
    assert secrets.resolve("") is None

def test_resolve_literal():
    # Anything that doesn't start with a known prefix is treated as literal
    assert secrets.resolve("sk-12345") == "sk-12345"
    assert secrets.resolve("Bearer token") == "Bearer token"

def test_resolve_env(monkeypatch):
    monkeypatch.setenv("TEST_DRAGOMAN_API_KEY", "env-secret-123")
    assert secrets.resolve("env:TEST_DRAGOMAN_API_KEY") == "env-secret-123"

def test_resolve_env_missing():
    # Missing env vars return None, they don't raise
    assert secrets.resolve("env:DOES_NOT_EXIST_ABC123") is None
