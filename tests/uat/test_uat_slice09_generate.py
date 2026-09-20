"""Slice 9 UAT: generate requires a session."""

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice09,
    pytest.mark.skipif(not slice_ready(9), reason=skip_reason(9)),
]


def test_generate_401_without_cookie(compose_stack: str) -> None:
    fake = "00000000-0000-0000-0000-000000000001"
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        assert (
            client.post(
                f"/api/papers/{fake}/generate",
                json={
                    "paper_type": "Empirical Study",
                    "sections": ["Abstract"],
                    "research_prompt": "x",
                },
            ).status_code
            == 401
        )
