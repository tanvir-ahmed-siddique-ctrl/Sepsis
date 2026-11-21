from app import auri


class _MemRecords:
    def __init__(self):
        self._data = {}

    def load_config(self, key):
        return self._data.get(key)

    def save_config(self, key, payload, updated_by):
        self._data[key] = payload


def test_auri_public_status_never_returns_key():
    records = _MemRecords()
    status = auri.save_site_llm(
        records,
        provider="openai",
        url="https://api.example.com/v1",
        model="gpt-test",
        api_key="sk-secret-should-not-leak",
        external_approved=True,
        embed_model=None,
        enabled=True,
        actor_id="admin",
    )
    assert status["has_api_key"] is True
    assert status["configured"] is True
    assert status["scores_sepsis"] is False
    assert "sk-secret" not in str(status)
    assert "api_key" not in status

    runtime = auri.runtime(records)
    assert runtime.api_key == "sk-secret-should-not-leak"
    assert runtime.source == "site"


def test_auri_clear_key():
    records = _MemRecords()
    auri.save_site_llm(
        records,
        provider="ollama",
        url="http://127.0.0.1:11434",
        model="qwen3.5:4b",
        api_key="temp",
        external_approved=False,
        embed_model=None,
        enabled=True,
        actor_id="admin",
    )
    status = auri.save_site_llm(
        records,
        provider="ollama",
        url="http://127.0.0.1:11434",
        model="qwen3.5:4b",
        api_key=None,
        external_approved=False,
        embed_model=None,
        enabled=True,
        actor_id="admin",
        clear_api_key=True,
    )
    assert status["has_api_key"] is False
    assert auri.runtime(records).api_key is None
