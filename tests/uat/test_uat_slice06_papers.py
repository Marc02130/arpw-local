"""Slice 6 UAT: papers require a confirmed session."""

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice06,
    pytest.mark.skipif(not slice_ready(6), reason=skip_reason(6)),
]


def test_papers_401_without_cookie(compose_stack: str) -> None:
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        assert client.get("/api/papers").status_code == 401
        assert (
            client.post(
                "/api/papers", json={"title": "x", "paper_type": "Empirical Study"}
            ).status_code
            == 401
        )
