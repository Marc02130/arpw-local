"""Live dogfood against Compose. Skip unless ARPW_DOGFOOD=1."""

import os

import httpx
import pytest

pytestmark = [pytest.mark.dogfood]


@pytest.mark.skipif(os.environ.get("ARPW_DOGFOOD") != "1", reason="set ARPW_DOGFOOD=1")
def test_health_on_8082() -> None:
    response = httpx.get("http://127.0.0.1:8082/api/health", timeout=5.0)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
