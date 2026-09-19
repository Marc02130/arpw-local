"""Slice 8 UAT: interrogation requires a session."""

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice08,
    pytest.mark.skipif(not slice_ready(8), reason=skip_reason(8)),
]


def test_interrogation_401_without_cookie(compose_stack: str) -> None:
    fake = "00000000-0000-0000-0000-000000000001"
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        assert client.get(f"/api/papers/{fake}/interrogation").status_code == 401
