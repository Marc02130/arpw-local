"""Slice 10 unit: citation lookup route and DOI extract."""

from app.services.bibliographic import extract_doi, extract_pmid
from tests.slices import skip_reason, slice_ready
import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice10,
    pytest.mark.skipif(not slice_ready(10), reason=skip_reason(10)),
]


def test_extract_doi_and_pmid() -> None:
    text = "See https://doi.org/10.1234/abcd.567 and PMID: 12345678 for details."
    assert extract_doi(text) == "10.1234/abcd.567"
    assert extract_pmid(text) == "12345678"


def test_lookup_401(client) -> None:
    response = client.post("/api/citations/lookup", json={"file_id": "00000000-0000-0000-0000-000000000001"})
    assert response.status_code == 401
