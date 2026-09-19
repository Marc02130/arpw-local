"""Slice 1 UAT: running Compose matches the scaffold contract."""

from __future__ import annotations

import httpx
import pytest

from tests import compose_support
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice01,
    pytest.mark.skipif(not slice_ready(1), reason=skip_reason(1)),
]


def test_api_health_is_proxied_on_8082(compose_stack: str) -> None:
    response = httpx.get(f"{compose_stack}/api/health", timeout=5.0)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_spa_placeholder_is_served(compose_stack: str) -> None:
    response = httpx.get(compose_stack, timeout=5.0)
    assert response.status_code == 200
    assert "AI Research Paper Writer" in response.text


def test_bare_api_path_redirects_to_slash(compose_stack: str) -> None:
    response = httpx.get(
        f"{compose_stack}/api", timeout=5.0, follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"].endswith("/api/")


def test_default_compose_does_not_publish_8000(compose_stack: str) -> None:
    ports = compose_support.published_ports()
    assert "8082" in ports
    assert "0.0.0.0:8000" not in ports
    assert ":::8000" not in ports


def test_fifty_six_mb_post_is_413(compose_stack: str) -> None:
    body = b"x" * (56 * 1024 * 1024)
    response = httpx.post(
        f"{compose_stack}/api/health",
        content=body,
        headers={"Content-Type": "application/octet-stream"},
        timeout=60.0,
    )
    assert response.status_code == 413
