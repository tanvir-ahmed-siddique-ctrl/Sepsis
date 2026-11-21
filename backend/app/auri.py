"""Auri AI — site-local assistant runtime (mapping / drafts / explain).

Credentials for optional cloud LLMs are stored encrypted in the hospital-local
config table. The browser never receives the raw API key. Sepsis scoring stays
on Frozen LightGBM Run 4 and never reads this module's secrets.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

CONFIG_KEY = "auri_ai_llm"
Provider = Literal["ollama", "openai"]


@dataclass(frozen=True)
class LlmRuntime:
    provider: Provider
    url: str | None
    model: str
    api_key: str | None
    external_approved: bool
    embed_model: str | None
    source: Literal["site", "env", "none"]
    enabled: bool


def _fernet() -> Fernet:
    material = (settings.account_encryption_key or settings.jwt_secret).encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material).digest()))


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def _env_runtime() -> LlmRuntime:
    url = settings.copilot_llm_url
    key = settings.copilot_llm_api_key.get_secret_value() if settings.copilot_llm_api_key else None
    return LlmRuntime(
        provider=settings.copilot_llm_provider,
        url=url,
        model=settings.copilot_llm_model,
        api_key=key,
        external_approved=settings.copilot_external_llm_approved,
        embed_model=settings.copilot_embed_model,
        source="env" if url else "none",
        enabled=bool(url),
    )


def load_site_document(records) -> dict[str, Any] | None:
    return records.load_config(CONFIG_KEY)


def public_status(records) -> dict[str, Any]:
    """Safe for API responses — never includes the API key."""
    env = _env_runtime()
    stored = load_site_document(records) or {}
    if stored.get("enabled"):
        return {
            "brand": "Auri AI",
            "mode": stored.get("provider", "ollama"),
            "model": stored.get("model") or env.model,
            "configured": True,
            "has_api_key": bool(stored.get("api_key_encrypted")),
            "external_approved": bool(stored.get("external_approved")),
            "url_host": _host(stored.get("url")),
            "source": "site",
            "local_default": stored.get("provider", "ollama") == "ollama",
            "scores_sepsis": False,
            "note": "Credentials stay on the hospital-local server. Auri AI never writes the sepsis score.",
        }
    return {
        "brand": "Auri AI",
        "mode": env.provider if env.enabled else "offline-retrieval",
        "model": env.model if env.enabled else None,
        "configured": env.enabled,
        "has_api_key": bool(env.api_key),
        "external_approved": env.external_approved,
        "url_host": _host(env.url),
        "source": env.source,
        "local_default": True,
        "scores_sepsis": False,
        "note": "Without a site key, Auri uses on-prem Ollama/env or deterministic retrieval only.",
    }


def _host(url: str | None) -> str | None:
    if not url:
        return None
    from urllib.parse import urlsplit

    return urlsplit(url).hostname


def save_site_llm(
    records,
    *,
    provider: Provider,
    url: str | None,
    model: str,
    api_key: str | None,
    external_approved: bool,
    embed_model: str | None,
    enabled: bool,
    actor_id: str,
    clear_api_key: bool = False,
) -> dict[str, Any]:
    previous = load_site_document(records) or {}
    encrypted = previous.get("api_key_encrypted")
    if clear_api_key:
        encrypted = None
    elif api_key:
        encrypted = _encrypt(api_key.strip())
    payload = {
        "enabled": enabled,
        "provider": provider,
        "url": (url or "").strip() or None,
        "model": model.strip() or settings.copilot_llm_model,
        "embed_model": (embed_model or "").strip() or None,
        "external_approved": bool(external_approved),
        "api_key_encrypted": encrypted,
        "brand": "Auri AI",
    }
    records.save_config(CONFIG_KEY, payload, actor_id)
    return public_status(records)


def runtime(records=None) -> LlmRuntime:
    """Prefer encrypted site config; fall back to process env."""
    if records is not None:
        stored = load_site_document(records) or {}
        if stored.get("enabled") and stored.get("url"):
            key = _decrypt(stored["api_key_encrypted"]) if stored.get("api_key_encrypted") else None
            return LlmRuntime(
                provider=stored.get("provider") or "ollama",
                url=stored.get("url"),
                model=stored.get("model") or settings.copilot_llm_model,
                api_key=key,
                external_approved=bool(stored.get("external_approved")),
                embed_model=stored.get("embed_model") or settings.copilot_embed_model,
                source="site",
                enabled=True,
            )
    return _env_runtime()
