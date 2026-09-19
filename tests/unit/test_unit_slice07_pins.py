"""Slice 7 unit: pins, isolation, pins-first retrieve."""

from __future__ import annotations

import pytest

from tests.fixtures.nfr7 import NFR7_TEXT
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice07,
    pytest.mark.skipif(not slice_ready(7), reason=skip_reason(7)),
]


def _upload_and_paper(client, source_role="literature"):
    uploaded = client.post(
        "/api/references",
        files={"file": ("nfr7.txt", NFR7_TEXT.encode(), "text/plain")},
        data={"source_role": source_role},
    )
    assert uploaded.status_code == 201
    paper = client.post(
        "/api/papers", json={"title": "Pins", "paper_type": "Empirical Study"}
    ).json()
    retrieved = client.post(
        f"/api/papers/{paper['paper_id']}/retrieve",
        json={
            "research_prompt": "nfr7probe",
            "paper_type": "Empirical Study",
            "sections": ["Methods"],
        },
    )
    passages = retrieved.json()["passages"]
    assert passages
    return paper, passages[0]


def test_pin_unpin_and_already_pinned(confirmed_client) -> None:
    paper, passage = _upload_and_paper(confirmed_client)
    created = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/pins",
        json={"vector_id": passage["vector_id"], "file_id": passage["file_id"]},
    )
    assert created.status_code == 201
    listed = confirmed_client.get(f"/api/papers/{paper['paper_id']}/pins")
    assert len(listed.json()) == 1
    again = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/pins",
        json={"vector_id": passage["vector_id"], "file_id": passage["file_id"]},
    )
    assert again.status_code == 409
    pin_id = created.json()["pin_id"]
    deleted = confirmed_client.delete(f"/api/papers/{paper['paper_id']}/pins/{pin_id}")
    assert deleted.status_code == 204
    assert confirmed_client.get(f"/api/papers/{paper['paper_id']}/pins").json() == []


def test_reject_interrogate_target_and_example_vector(confirmed_client) -> None:
    paper, passage = _upload_and_paper(confirmed_client)
    bad = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/pins",
        json={
            "vector_id": passage["vector_id"],
            "file_id": passage["file_id"],
            "target_section": "Interrogate",
        },
    )
    assert bad.status_code == 400
    example = confirmed_client.post(
        "/api/examples",
        files={"file": ("voice.txt", ("Style example paragraph. " * 20).encode(), "text/plain")},
    )
    assert example.status_code == 201
    bogus = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/pins",
        json={"vector_id": passage["vector_id"], "file_id": example.json()["file_id"]},
    )
    assert bogus.status_code == 400


def test_pin_first_in_retrieve(confirmed_client) -> None:
    paper, passage = _upload_and_paper(confirmed_client)
    confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/pins",
        json={"vector_id": passage["vector_id"], "file_id": passage["file_id"]},
    )
    retrieved = confirmed_client.post(
        f"/api/papers/{paper['paper_id']}/retrieve",
        json={
            "research_prompt": "unrelated query that still returns the pin first",
            "paper_type": "Empirical Study",
            "sections": ["Discussion"],
        },
    )
    assert retrieved.status_code == 200
    first = retrieved.json()["passages"][0]
    assert first["vector_id"] == passage["vector_id"]
    assert first["pinned"] is True


def test_pin_isolation_other_user(confirmed_client, client, monkeypatch) -> None:
    paper, passage = _upload_and_paper(confirmed_client)
    # second confirmed user
    import uuid
    from urllib.parse import parse_qs, urlparse

    captured: dict[str, str] = {}

    def fake_send(to: str, subject: str, body: str) -> None:
        captured["body"] = body

    monkeypatch.setattr("app.mailer.send_mail", fake_send)
    email = f"other-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse", "full_name": "Other User"},
    )
    token = parse_qs(urlparse(captured["body"].split()[-1].strip()).query)["token"][0]
    client.get(f"/api/auth/confirm?token={token}", follow_redirects=False)
    client.post("/api/auth/login", json={"email": email, "password": "correct-horse"})
    other_paper = client.post(
        "/api/papers", json={"title": "Other", "paper_type": "Empirical Study"}
    ).json()
    stolen = client.post(
        f"/api/papers/{other_paper['paper_id']}/pins",
        json={"vector_id": passage["vector_id"], "file_id": passage["file_id"]},
    )
    assert stolen.status_code == 400
    listed = client.get(f"/api/papers/{paper['paper_id']}/pins")
    assert listed.status_code == 404
