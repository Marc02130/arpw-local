"""Slice 1 unit: Compose/nginx/env/health stub. No Docker."""

from __future__ import annotations

import inspect
import re

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, health
from tests.paths import COMPOSE, COMPOSE_DEV, ENV_EXAMPLE, NGINX, ROOT

pytestmark = [pytest.mark.unit, pytest.mark.slice01]


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


def test_health_is_async_and_has_no_io() -> None:
    assert inspect.iscoroutinefunction(health)
    source = inspect.getsource(health)
    assert "sqlalchemy" not in source.lower()
    assert "openai" not in source.lower()
    assert "await " not in source


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_compose_publishes_only_8080_and_mailpit() -> None:
    services = _compose()["services"]
    assert services["web"]["ports"] == ["8080:80"]
    assert services["mail"]["ports"] == ["8025:8025"]
    assert "ports" not in services["api"]
    assert "ports" not in services["db"]


def test_compose_constructs_database_url_from_postgres_vars() -> None:
    env = _compose()["services"]["api"]["environment"]
    url = env["DATABASE_URL"]
    assert url.startswith("postgresql+psycopg://")
    assert "${POSTGRES_USER}" in url
    assert "${POSTGRES_PASSWORD}" in url
    assert "${POSTGRES_DB}" in url
    assert "@db:5432" in url


def test_api_healthcheck_is_stdlib_urllib() -> None:
    hc = _compose()["services"]["api"]["healthcheck"]
    joined = " ".join(hc["test"])
    assert "urllib.request" in joined
    assert "curl" not in joined
    assert hc["interval"] == "5s"
    assert hc["timeout"] == "3s"
    assert hc["retries"] == 12
    assert hc["start_period"] == "20s"


def test_web_waits_for_api_healthy() -> None:
    depends = _compose()["services"]["web"]["depends_on"]
    assert depends["api"]["condition"] == "service_healthy"


def test_dev_overlay_only_publishes_api_8001() -> None:
    data = yaml.safe_load(COMPOSE_DEV.read_text())
    assert list(data["services"]) == ["api"]
    assert data["services"]["api"] == {"ports": ["8001:8000"]}


def test_nginx_body_timeout_and_forwarded_headers() -> None:
    text = NGINX.read_text()
    assert "client_max_body_size 55m;" in text
    assert "proxy_read_timeout 600s;" in text
    assert "proxy_ignore_client_abort on;" in text
    assert "location = /api { return 308 /api/; }" in text
    assert "X-Forwarded-Proto $scheme" in text
    assert "X-Forwarded-For $proxy_add_x_forwarded_for" in text
    assert "proxy_pass_header Set-Cookie" not in text
    assert 'Cache-Control "public, max-age=31536000, immutable"' in text


def test_env_example_has_required_keys_and_no_chat_secrets() -> None:
    text = ENV_EXAMPLE.read_text()
    assert "PUBLIC_ORIGINS=http://localhost:8080,http://localhost:3000" in text
    assert "JWT_SECRET=" in text
    assert "COOKIE_SECURE=" in text
    assert "POSTGRES_USER=" in text
    assert "OPENAI_API_KEY" not in text
    assert "XAI_API_KEY" not in text
    assert "ANTHROPIC_API_KEY" not in text
    assignments = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    joined = "\n".join(assignments)
    assert not re.search(r"^DATABASE_URL=", joined, re.M)
    assert "VITE_" not in joined
    assert "NEXT_PUBLIC_" not in joined


def test_upload_body_limit_is_one_file() -> None:
    assert settings.MAX_FILE_SIZE == 10_485_760
    assert settings.MAX_UPLOAD_BODY_BYTES == 12_582_912


def test_conversion_runtime_files_do_not_mention_vite() -> None:
    for path in (COMPOSE, COMPOSE_DEV, NGINX, ROOT / "api" / "app" / "main.py"):
        assert "vite" not in path.read_text().lower()
