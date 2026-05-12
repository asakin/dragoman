import pytest
from dragoman import routing

def test_parse_simple():
    conn, model = routing.parse("openai:gpt-4o")
    assert conn == "openai"
    assert model == "gpt-4o"

def test_parse_missing_colon():
    with pytest.raises(ValueError, match="must be 'connection:name'"):
        routing.parse("gpt-4o")

def test_parse_with_known_connections():
    # If a connection name itself contains a colon (like localhost:11434),
    # the known_connections list ensures we parse it correctly.
    known = ["local", "localhost:11434"]
    
    conn, model = routing.parse("localhost:11434:llama3", known_connections=known)
    assert conn == "localhost:11434"
    assert model == "llama3"

    conn, model = routing.parse("local:llama3", known_connections=known)
    assert conn == "local"
    assert model == "llama3"
