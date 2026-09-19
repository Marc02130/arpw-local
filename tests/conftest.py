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
