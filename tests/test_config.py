from dragoman import config

def test_normalize_host_valid():
    assert config.normalize_host("https://api.openai.com/v1") == "https://api.openai.com/v1"
    assert config.normalize_host("http://localhost:11434/v1") == "http://localhost:11434/v1"

def test_normalize_host_adds_http():
    # Should prepend http://
    assert config.normalize_host("localhost:11434") == "http://localhost:11434"
    assert config.normalize_host("127.0.0.1:11435") == "http://127.0.0.1:11435"

def test_normalize_host_invalid():
    # Reject strings that are obviously not URLs or hosts
    assert config.normalize_host("LiteLLM") is None
    assert config.normalize_host("skip") is None
    assert config.normalize_host("") is None
    assert config.normalize_host(None) is None
