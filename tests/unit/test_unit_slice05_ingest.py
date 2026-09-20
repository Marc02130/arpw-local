"""Slice 5 unit: one-file upload, IMRaD ingest, MiniLM model string."""

from __future__ import annotations

import pytest

from tests.fixtures.nfr7 import NFR7_BIBLIOGRAPHY, NFR7_PROBE, NFR7_TEXT, build_fixture_pdf
from tests.paths import DOCUMENTS_ROUTER
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice05,
    pytest.mark.skipif(not slice_ready(5), reason=skip_reason(5)),
]


def test_documents_router_is_one_file_post() -> None:
    text = DOCUMENTS_ROUTER.read_text()
    assert 'File(...)' in text
    assert "files: list" not in text
    assert "all(row.status == \"failed\"" not in text
    assert "Literature cap of 500 files reached" in text
    assert "Original research cap of 100 files reached" in text


def _upload_txt(client, name: str, body: str, source_role: str = "literature"):
    return client.post(
        "/api/references",
        files={"file": (name, body.encode(), "text/plain")},
        data={"source_role": source_role},
    )


def test_upload_txt_ready_minilm_string(confirmed_client) -> None:
    response = _upload_txt(confirmed_client, "paper.txt", NFR7_TEXT)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 1
    assert body["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert body["source_role"] == "literature"
    assert "file_path" not in body


def test_imrad_does_not_mix_methods_and_references(confirmed_client, postgres_url) -> None:
    from sqlalchemy import create_engine, text

    response = _upload_txt(confirmed_client, "nfr7.txt", NFR7_TEXT)
    assert response.status_code == 201
    file_id = response.json()["file_id"]
    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT section, chunk_text FROM reference_vectors WHERE file_id = :fid"
            ),
            {"fid": file_id},
        ).fetchall()
    methods = [r[1] for r in rows if r[0] == "Methods"]
    refs = [r[1] for r in rows if r[0] == "References"]
    assert methods
    assert refs
    assert any(NFR7_PROBE in m for m in methods)
    assert all(NFR7_BIBLIOGRAPHY not in m for m in methods)
    assert any(NFR7_BIBLIOGRAPHY in r for r in refs)


def test_upload_pdf_fixture(confirmed_client) -> None:
    pdf = build_fixture_pdf()
    response = confirmed_client.post(
        "/api/references",
        files={"file": ("nfr7.pdf", pdf, "application/pdf")},
        data={"source_role": "literature"},
    )
    assert response.status_code == 201
    assert response.json()["status"] in {"ready", "failed"}
    if response.json()["status"] == "ready":
        assert response.json()["chunk_count"] >= 1


def test_primary_source_role(confirmed_client) -> None:
    response = _upload_txt(
        confirmed_client, "study.txt", "Methods\n\nPrimary study methods paragraph " * 8,
        source_role="primary",
    )
    assert response.status_code == 201
    assert response.json()["source_role"] == "primary"


def test_unsupported_type_415(confirmed_client) -> None:
    response = confirmed_client.post(
        "/api/references",
        files={"file": ("x.bin", b"\x00\x01\x02\x03", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_empty_file_413(confirmed_client) -> None:
    response = confirmed_client.post(
        "/api/references",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 413


def test_example_upload_and_delete(confirmed_client) -> None:
    response = confirmed_client.post(
        "/api/examples",
        files={"file": ("voice.txt", ("Style example paragraph. " * 20).encode(), "text/plain")},
    )
    assert response.status_code == 201
    file_id = response.json()["file_id"]
    listed = confirmed_client.get("/api/examples")
    assert any(row["file_id"] == file_id for row in listed.json())
    deleted = confirmed_client.delete(f"/api/examples/{file_id}")
    assert deleted.status_code == 204
    listed = confirmed_client.get("/api/examples")
    assert all(row["file_id"] != file_id for row in listed.json())
