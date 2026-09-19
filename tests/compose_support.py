"""Start the Compose stack for UAT and dogfood tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import time

import httpx

from tests.paths import ENV_EXAMPLE, ROOT

BASE_URL = "http://127.0.0.1:8080"


def docker_available() -> bool:
    return shutil.which("docker") is not None


def ensure_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(ENV_EXAMPLE.read_text())


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def published_ports() -> str:
    result = compose("ps", "--format", "{{.Name}} {{.Ports}}", check=False)
    return (result.stdout or "") + (result.stderr or "")


def wait_for_health(timeout: float = 300.0) -> None:
    deadline = time.time() + timeout
    last_error = "not reached"
    while time.time() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/api/health", timeout=2.0)
            if response.status_code == 200 and response.json().get("status") == "ok":
                return
            last_error = f"status {response.status_code} body {response.text!r}"
        except Exception as exc:  # noqa: BLE001 — wait loop
            last_error = str(exc)
        time.sleep(2)
    raise TimeoutError(f"Compose stack did not become healthy: {last_error}")


def up() -> str:
    ensure_env()
    result = compose("up", "--build", "-d")
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose up failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    wait_for_health()
    return BASE_URL


def down() -> None:
    compose("down", check=False)


def keep_compose() -> bool:
    return os.environ.get("ARPW_KEEP_COMPOSE") == "1"


def psql(sql: str) -> str:
    result = compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        os.environ.get("POSTGRES_USER", "arpw"),
        "-d",
        os.environ.get("POSTGRES_DB", "arpw"),
        "-c",
        sql,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout
