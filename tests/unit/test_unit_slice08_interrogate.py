"""Slice 8 unit: interrogate key-first, literature default, notes persist."""

from __future__ import annotations

import pytest

from tests.fixtures.nfr7 import NFR7_TEXT
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice08,
    pytest.mark.skipif(not slice_ready(8), reason=skip_reason(8)),
]


def _paper_with_both_roles(client):
    client.post(
        "/api/references",
        files={"file": ("lit.txt", NFR7_TEXT.encode(), "text/plain")},
        data={"source_role": "literature"},
    )
    client.post(
        "/api/references",
        files={
            "file": (
                "prim.txt",
                ("Methods\n\nPrimary-only secret token prim7probe lives here. " * 12).encode(),
                "text/plain",
            )
        },
        data={"source_role": "primary"},
    )
    return client.post(
        "/api/papers", json={"title": "Ask", "paper_type": "Empirical Study"}
    ).json()


def test_missing_key_before_retrieve(confirmed_client) -> None:
    paper = confirmed_client.post(
        "/api/papers", json={"title": "Ask", "paper_type": "Empirical Study"}
    ).json()
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/interrogation",
        json={"question": "What is nfr7probe?"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "missing_llm_key"


def test_default_sources_omit_primary(confirmed_client, monkeypatch) -> None:
    confirmed_client.put(
        "/api/settings/llm",
        json={"xai_api_key": "xai-live-key-for-tests", "chat_provider": "xai"},
    )
    paper = _paper_with_both_roles(confirmed_client)

    def fake_complete(prompt, user, llm):
        return "The token is [S1] and also [S99]."

    monkeypatch.setattr("app.services.chat.complete", fake_complete)
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/interrogation",
        json={"question": "What is nfr7probe?"},
    )
    assert response.status_code == 200
    body = response.json()
    blob = " ".join(p["chunk_text"] for p in body["passages"])
    assert "nfr7probe" in blob
    assert "prim7probe" not in blob
    assert all(p["source_role"] == "literature" for p in body["passages"])
    assert "[S99]" not in body["answer"]
    turns = confirmed_client.get(f"/api/papers/{paper['paper_id']}/interrogation")
    assert len(turns.json()) == 2
    assert turns.json()[0]["role"] == "user"


def test_all_sources_can_include_primary(confirmed_client, monkeypatch) -> None:
    confirmed_client.put(
        "/api/settings/llm",
        json={"xai_api_key": "xai-live-key-for-tests", "chat_provider": "xai"},
    )
    paper = _paper_with_both_roles(confirmed_client)
    monkeypatch.setattr("app.services.chat.complete", lambda *a, **k: "ok")
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/interrogation",
        json={
            "question": "nfr7probe and prim7probe",
            "filter_role": "both",
        },
    )
    assert response.status_code == 200
    roles = {p["source_role"] for p in response.json()["passages"]}
    assert "literature" in roles
    assert "primary" in roles


def test_empty_retrieve_skips_complete(confirmed_client, monkeypatch) -> None:
    confirmed_client.put(
        "/api/settings/llm",
        json={"xai_api_key": "xai-live-key-for-tests", "chat_provider": "xai"},
    )
    paper = confirmed_client.post(
        "/api/papers", json={"title": "Empty", "paper_type": "Empirical Study"}
    ).json()
    called = {"n": 0}

    def fake_complete(*args, **kwargs):
        called["n"] += 1
        return "should not run"

    monkeypatch.setattr("app.services.chat.complete", fake_complete)
    response = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/interrogation",
        json={"question": "nothing is indexed"},
    )
    assert response.status_code == 200
    assert called["n"] == 0
    assert "Upload and index research papers" in response.json()["answer"]
