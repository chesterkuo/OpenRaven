from __future__ import annotations

from openraven.config import RavenConfig


def test_default_provider_is_gemini(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.llm_provider == "gemini"
    assert config.ollama_base_url == "http://localhost:11434"


def test_env_var_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENRAVEN_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENRAVEN_LLM_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OPENRAVEN_WIKI_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OPENRAVEN_EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OPENRAVEN_OLLAMA_URL", "http://gpu-box:11434")

    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.llm_provider == "ollama"
    assert config.llm_model == "llama3.2:3b"
    assert config.wiki_llm_model == "llama3.2:3b"
    assert config.embedding_model == "nomic-embed-text"
    assert config.ollama_base_url == "http://gpu-box:11434"


def test_explicit_args_override_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENRAVEN_LLM_PROVIDER", "ollama")
    config = RavenConfig(working_dir=tmp_path / "kb", llm_provider="gemini")
    assert config.llm_provider == "gemini"


def test_api_key_property(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.llm_api_key == "test-key-123"


def test_api_key_empty_for_ollama(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb", llm_provider="ollama")
    assert config.llm_api_key == ""


def test_google_oauth_config_fields(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.google_client_id == ""
    assert config.google_client_secret == ""
    assert config.google_token_path == config.working_dir / "google_token.json"


def test_google_oauth_env_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id-123")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret-456")
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.google_client_id == "test-id-123"
    assert config.google_client_secret == "test-secret-456"


def test_otter_key_path(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.otter_key_path == config.working_dir / "otter_api_key"


def test_otter_api_key_returns_empty_when_no_file(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.otter_api_key == ""
