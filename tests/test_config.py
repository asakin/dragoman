"""Tests for config save/load round-trip and value resolution."""

from pathlib import Path

from dragoman import config


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    """Config should survive a save → load cycle with all value types."""
    cfg_dir = tmp_path / ".config" / "dragoman"
    cfg_file = cfg_dir / "config.toml"

    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_file)

    original = {
        "providers": {
            "perplexity": {
                "type": "openai_compat",
                "host": "https://api.perplexity.ai",
                "api_key": "op://Personal/Perplexity/credential",
                "approved_models": ["sonar", "sonar-pro"],
            },
            "ollama": {
                "type": "openai_compat",
                "host": "http://localhost:11434/v1",
            },
        }
    }

    config.save_config(original)
    loaded = config.load_config()

    assert loaded["providers"]["perplexity"]["type"] == "openai_compat"
    assert loaded["providers"]["perplexity"]["host"] == "https://api.perplexity.ai"
    assert loaded["providers"]["perplexity"]["api_key"] == "op://Personal/Perplexity/credential"
    assert loaded["providers"]["perplexity"]["approved_models"] == ["sonar", "sonar-pro"]
    assert loaded["providers"]["ollama"]["host"] == "http://localhost:11434/v1"


def test_load_missing_config(tmp_path, monkeypatch):
    """Loading from a nonexistent file should return an empty dict, not crash."""
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "nope" / "config.toml")

    result = config.load_config()

    assert result == {}


def test_get_value_env_override(tmp_path, monkeypatch):
    """Env var should override config file value."""
    cfg_dir = tmp_path / ".config" / "dragoman"
    cfg_file = cfg_dir / "config.toml"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_file)

    config.save_config({
        "providers": {
            "test_provider": {
                "host": "https://from-config.example.com",
            }
        }
    })

    monkeypatch.setenv("DRAGOMAN_TEST_HOST", "https://from-env.example.com")

    # Env var wins
    val = config.get_value("providers", "host", env_var="DRAGOMAN_TEST_HOST")
    assert val == "https://from-env.example.com"
