"""Slice 5 UAT: upload requires a confirmed session."""

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice05,
    pytest.mark.skipif(not slice_ready(5), reason=skip_reason(5)),
]


def test_upload_401_without_cookie(compose_stack: str) -> None:
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        response = client.post(
            "/api/references",
            files={"file": ("paper.txt", b"hello world " * 20, "text/plain")},
        )
        assert response.status_code == 401
