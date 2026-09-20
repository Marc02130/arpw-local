"""Slice 6 unit: papers CRUD and MiniLM-only retrieve."""

from __future__ import annotations

import pytest

from tests.fixtures.nfr7 import NFR7_TEXT
from tests.paths import PAPERS_ROUTER, ROOT
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice06,
    pytest.mark.skipif(not slice_ready(6), reason=skip_reason(6)),
]


def test_retrieve_has_no_hash_fallback() -> None:
    text = (ROOT / "api" / "app" / "services" / "retrieve.py").read_text()
    assert "matchWithModelFallback" not in text
    assert "hash-384" not in text
    assert "filter_model" in text
    assert "hashEmbedding" not in text
    assert PAPERS_ROUTER.exists()


def test_unknown_paper_type_422(confirmed_client) -> None:
    response = confirmed_client.post(
        "/api/papers", json={"title": "Nope", "paper_type": "Blog Post"}
    )
    assert response.status_code == 422


def test_create_lists_and_patches_paper(confirmed_client) -> None:
    created = confirmed_client.post(
        "/api/papers",
        json={"title": "  ", "paper_type": "Literature Review"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Untitled paper"
    assert body["paper_type"] == "Literature Review"
    assert body["citation_style"] == "APA"
    assert body["output_format"] == "markdown"
    assert body["attribution"] == []
    assert "Abstract" in body["sections"]
    paper_id = body["paper_id"]

    listed = confirmed_client.get("/api/papers")
    assert any(row["paper_id"] == paper_id for row in listed.json())

    patched = confirmed_client.patch(
        f"/api/papers/{paper_id}",
        json={
            "title": "My review",
            "research_prompt": "What is known about nfr7probe?",
            "citation_style": "APA",
            "sections": ["Abstract", "Introduction", "Literature Review"],
        },
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "My review"
    assert patched.json()["paper_type"] == "Literature Review"

    got = confirmed_client.get(f"/api/papers/{paper_id}")
    assert got.json()["research_prompt"].startswith("What is known")


def test_retrieve_hits_nfr7probe_and_skips_primary_for_lit_review(confirmed_client) -> None:
    confirmed_client.post(
        "/api/references",
        files={"file": ("nfr7.txt", NFR7_TEXT.encode(), "text/plain")},
        data={"source_role": "literature"},
    )
    confirmed_client.post(
        "/api/references",
        files={
            "file": (
                "primary.txt",
                ("Methods\n\nPrimary-only secret token prim7probe appears here. " * 12).encode(),
                "text/plain",
            )
        },
        data={"source_role": "primary"},
    )
    paper = confirmed_client.post(
        "/api/papers", json={"title": "Probe", "paper_type": "Literature Review"}
    ).json()
    retrieved = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/retrieve",
        json={
            "research_prompt": "nfr7probe retrieval hit",
            "paper_type": "Literature Review",
            "sections": ["Literature Review", "Introduction"],
        },
    )
    assert retrieved.status_code == 200
    passages = retrieved.json()["passages"]
    blob = " ".join(p["chunk_text"] for p in passages)
    assert "nfr7probe" in blob
    assert all(p["source_role"] == "literature" for p in passages)
    assert "prim7probe" not in blob


def test_delete_and_regenerate(confirmed_client) -> None:
    paper = confirmed_client.post(
        "/api/papers", json={"title": "v1", "paper_type": "Empirical Study"}
    ).json()
    regen = confirmed_client.post(f"/api/papers/{paper['paper_id']}/regenerate")
    assert regen.status_code == 201
    assert regen.json()["version"] == 2
    assert regen.json()["title"] == "v1"
    deleted = confirmed_client.delete(f"/api/papers/{paper['paper_id']}")
    assert deleted.status_code == 204
