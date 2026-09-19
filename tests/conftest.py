import os
import sys
from pathlib import Path

import pytest

from tests import compose_support

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

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
