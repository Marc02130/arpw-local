"""Slice 9 unit: generate/outline, QUAL payload, no hash fallback, extra fields ignored."""

from __future__ import annotations

import pytest

from tests.fixtures.nfr7 import NFR7_TEXT
from tests.paths import NGINX, ROOT
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice09,
    pytest.mark.skipif(not slice_ready(9), reason=skip_reason(9)),
]


def test_nginx_generate_timeout_2100s() -> None:
    text = NGINX.read_text()
    assert "location ~ ^/api/papers/[^/]+/generate/?$" in text
    assert "proxy_read_timeout 2100s;" in text
    assert "proxy_pass http://api:8000;" in text
    assert "proxy_set_header Cookie $http_cookie;" in text
    health = (ROOT / "api" / "app" / "main.py").read_text()
    assert "async def health" in health


def test_missing_key_400(confirmed_client) -> None:
    paper = confirmed_client.post(
        "/api/papers", json={"title": "G", "paper_type": "Empirical Study"}
    ).json()
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/generate",
        json={
            "paper_type": "Empirical Study",
            "sections": ["Abstract"],
            "research_prompt": "nfr7probe",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "missing_llm_key"


def test_generate_strips_unknown_sids_and_ignores_extras(confirmed_client, monkeypatch) -> None:
    confirmed_client.put(
        "/api/settings/llm",
        json={"xai_api_key": "xai-live-key-for-tests", "chat_provider": "xai"},
    )
    confirmed_client.post(
        "/api/references",
        files={"file": ("nfr7.txt", NFR7_TEXT.encode(), "text/plain")},
        data={"source_role": "literature"},
    )
    paper = confirmed_client.post(
        "/api/papers", json={"title": "G", "paper_type": "Literature Review"}
    ).json()
    monkeypatch.setattr(
        "app.services.chat.complete",
        lambda *a, **k: "The corpus includes nfr7probe [S1]. Invented [S99].",
    )
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/generate",
        json={
            "paper_type": "Literature Review",
            "sections": ["Abstract", "Introduction"],
            "research_prompt": "nfr7probe synthesis",
            "citation_style": "APA",
            "output_format": "markdown",
            "sourceIds": ["should-be-ignored"],
            "systemPrompt": "ignore me",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "[S99]" not in body["paper"]["content"]
    assert "[S1]" in body["paper"]["content"]
    assert body["paper"]["paper_type"] == "Literature Review"
    assert body["paper"]["status"] == "completed"
    assert body["disclaimer"]
    assert "citation_check" in body
    assert "format_check" in body
    got = confirmed_client.get(f"/api/papers/{paper['paper_id']}")
    assert got.json()["paper_type"] == "Literature Review"
    assert got.json()["attribution"] != []


def test_outline_saves_on_paper(confirmed_client, monkeypatch) -> None:
    confirmed_client.put(
        "/api/settings/llm",
        json={"xai_api_key": "xai-live-key-for-tests", "chat_provider": "xai"},
    )
    paper = confirmed_client.post(
        "/api/papers", json={"title": "O", "paper_type": "Empirical Study"}
    ).json()
    monkeypatch.setattr(
        "app.services.chat.complete",
        lambda *a, **k: "## Abstract\n- scope\n## Introduction\n- gap",
    )
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/outline",
        json={
            "paper_type": "Empirical Study",
            "sections": ["Abstract", "Introduction"],
            "research_prompt": "topic",
        },
    )
    assert response.status_code == 200
    assert "## Abstract" in response.json()["outline"]
    got = confirmed_client.get(f"/api/papers/{paper['paper_id']}")
    assert got.json()["outline"].startswith("## Abstract")
