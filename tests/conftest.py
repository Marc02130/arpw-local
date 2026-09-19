import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests import compose_support

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://arpw:changeme@127.0.0.1:5432/arpw",
)
os.environ.setdefault("JWT_SECRET", "dev-secret-dev-secret-dev-secret-xx")
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")
_upload_root = Path("/tmp/arpw-test-uploads")
_upload_root.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("UPLOAD_ROOT", str(_upload_root))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: fast tests with no Docker")
    config.addinivalue_line("markers", "uat: user-acceptance against the Compose stack")
    config.addinivalue_line("markers", "dogfood: live operator walkthrough of the running stack")


@pytest.fixture(scope="session")
def compose_stack():
    if not compose_support.docker_available():
        pytest.skip("docker is not available")
    url = compose_support.up()
    yield url
    if not compose_support.keep_compose():
        compose_support.down()


def _psycopg_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _alembic_upgrade(url: str) -> None:
    api_root = str(API_ROOT)
    saved = sys.path[:]
    try:
        sys.path[:] = [p for p in sys.path if p != api_root]
        from alembic import command
        from alembic.config import Config
    finally:
        sys.path[:] = saved

    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """pgvector via Testcontainers (or compose db if ARPW_USE_COMPOSE_DB=1)."""
    if not shutil.which("docker"):
        pytest.skip("docker is not available")

    if os.environ.get("ARPW_USE_COMPOSE_DB") == "1" and os.environ.get("DATABASE_URL"):
        url = _psycopg_url(os.environ["DATABASE_URL"])
        _alembic_upgrade(url)
        yield url
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        url = _psycopg_url(postgres.get_connection_url())
        os.environ["DATABASE_URL"] = url
        _alembic_upgrade(url)
        yield url


@pytest.fixture
def client(postgres_url: str):
    from fastapi.testclient import TestClient

    from app import db
    from app.main import app

    db.configure_engine(postgres_url)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def confirmed_client(client, monkeypatch):
    import uuid
    from urllib.parse import parse_qs, urlparse

    captured: dict[str, str] = {}

    def fake_send(to: str, subject: str, body: str) -> None:
        captured["body"] = body

    monkeypatch.setattr("app.mailer.send_mail", fake_send)
    email = f"user-{uuid.uuid4().hex[:12]}@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse", "full_name": "Ada Lovelace"},
    )
    token = None
    for part in captured["body"].split():
        if "token=" in part:
            token = parse_qs(urlparse(part.strip()).query)["token"][0]
            break
    assert token
    client.get(f"/api/auth/confirm?token={token}", follow_redirects=False)
    login = client.post("/api/auth/login", json={"email": email, "password": "correct-horse"})
    assert login.status_code == 200
    client.email = email
    yield client
