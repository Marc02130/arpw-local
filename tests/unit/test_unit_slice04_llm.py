"""Slice 4 unit: encrypted LLM keys, last4, no env fallback."""

from __future__ import annotations

import pytest

from tests.paths import SETTINGS_ROUTER
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice04,
    pytest.mark.skipif(not slice_ready(4), reason=skip_reason(4)),
]


def test_settings_router_has_no_env_fallback() -> None:
    keys = (SETTINGS_ROUTER.parents[1] / "services" / "llm_keys.py").read_text()
    assert "OPENAI_API_KEY" not in keys
    assert "XAI_API_KEY" not in keys
    assert "ANTHROPIC_API_KEY" not in keys
    assert "decrypt_secret" in keys
    assert "last4" in keys


def test_unauthenticated_settings_401(client) -> None:
    response = client.get("/api/settings/llm")
    assert response.status_code == 401


def test_get_settings_has_no_secrets(confirmed_client) -> None:
    response = confirmed_client.get("/api/settings/llm")
    assert response.status_code == 200
    body = response.json()
    assert "openai_api_key" not in body
    assert "xai_api_key" not in body
    assert set(body) >= {"openai", "xai", "anthropic", "chat_provider", "chat_models"}
    assert body["chat_provider"] == "xai"
    assert body["chat_models"]["xai"] == "grok-4.3"
    assert body["chat_models"]["anthropic"] == "claude-sonnet-4-5"
    assert body["xai"]["configured"] is False
    assert body["xai"]["last4"] is None


def test_put_keys_and_select_provider(confirmed_client) -> None:
    saved = confirmed_client.put(
        "/api/settings/llm",
        json={
            "openai_api_key": "sk-live-openai-not-a-placeholder-key",
            "xai_api_key": "xai-live-key-for-tests",
            "anthropic_api_key": "sk-ant-live-key-for-tests",
            "chat_provider": "xai",
        },
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["openai"]["configured"] is True
    assert body["xai"]["configured"] is True
    assert body["anthropic"]["configured"] is True
    assert body["xai"]["last4"] == "ests"
    assert body["chat_provider"] == "xai"
    assert "xai-live-key" not in saved.text
    assert "sk-live-openai" not in saved.text

    again = confirmed_client.get("/api/settings/llm")
    assert again.json()["chat_provider"] == "xai"
    assert again.json()["xai"]["last4"] == "ests"
    assert "xai-live-key" not in again.text


def test_cannot_select_provider_without_key(confirmed_client) -> None:
    response = confirmed_client.put("/api/settings/llm", json={"chat_provider": "anthropic"})
    assert response.status_code == 422
    assert "no API key configured" in response.json()["detail"]


def test_xai_key_must_start_with_xai(confirmed_client) -> None:
    response = confirmed_client.put(
        "/api/settings/llm", json={"xai_api_key": "sk-not-an-xai-key"}
    )
    assert response.status_code == 422


def test_path_like_key_rejected(confirmed_client) -> None:
    response = confirmed_client.put(
        "/api/settings/llm", json={"openai_api_key": "/secrets/openai.key"}
    )
    assert response.status_code == 422


def test_clear_key(confirmed_client) -> None:
    confirmed_client.put(
        "/api/settings/llm", json={"anthropic_api_key": "sk-ant-live-key-for-tests"}
    )
    cleared = confirmed_client.put("/api/settings/llm", json={"anthropic_api_key": ""})
    assert cleared.status_code == 200
    assert cleared.json()["anthropic"]["configured"] is False
    assert cleared.json()["anthropic"]["last4"] is None
