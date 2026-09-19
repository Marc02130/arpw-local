"""Slice 7 UAT: pins require a confirmed session."""

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice07,
    pytest.mark.skipif(not slice_ready(7), reason=skip_reason(7)),
]


def test_pins_401_without_cookie(compose_stack: str) -> None:
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        fake = "00000000-0000-0000-0000-000000000001"
        assert client.get(f"/api/papers/{fake}/pins").status_code == 401
