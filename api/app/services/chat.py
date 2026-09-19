from __future__ import annotations

import httpx
from openai import APITimeoutError, OpenAI

from app.config import settings
from app.models import User, UserLlmSettings
from app.services.llm_keys import CHAT_MODELS, resolve_key

CHAT_TIMEOUT_MESSAGE = "Chat request timed out after 2 minutes"


class MissingLlmKey(Exception):
    def __init__(self, provider: str):
        label = {"openai": "OpenAI", "xai": "xAI", "anthropic": "Anthropic"}.get(provider, provider)
        super().__init__(f"Save an API key for {label} on Profile before generating.")
        self.provider = provider
        self.code = "missing_llm_key"


def complete(prompt: str, user: User, llm: UserLlmSettings | None) -> str:
    provider = llm.chat_provider if llm else "xai"
    key = resolve_key(llm, provider)
    if not key:
        raise MissingLlmKey(provider)
    model = CHAT_MODELS[provider]
    timeout = settings.CHAT_TIMEOUT_SECONDS
    try:
        if provider == "anthropic":
            return _anthropic(prompt, key, model, timeout)
        if provider == "xai":
            client = OpenAI(api_key=key, base_url=settings.XAI_BASE_URL, timeout=timeout)
            return _openai_chat(client, model, prompt)
        client = OpenAI(api_key=key, timeout=timeout)
        return _openai_chat(client, model, prompt)
    except (httpx.TimeoutException, APITimeoutError) as exc:
        raise TimeoutError(CHAT_TIMEOUT_MESSAGE) from exc


def _openai_chat(client: OpenAI, model: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=settings.CHAT_TEMPERATURE,
        max_tokens=settings.CHAT_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _anthropic(prompt: str, key: str, model: str, timeout: float) -> str:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            settings.ANTHROPIC_API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": settings.ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": settings.CHAT_MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Chat request failed ({response.status_code})")
        data = response.json()
    blocks = data.get("content") or []
    texts = [block.get("text", "") for block in blocks if block.get("type") == "text"]
    return "".join(texts)
