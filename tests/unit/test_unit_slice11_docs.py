"""Slice 11: docs, smoke, UAT waits."""

import pytest

from tests.paths import ROOT, SMOKE

pytestmark = [pytest.mark.unit, pytest.mark.slice11]


def test_smoke_script_and_ports() -> None:
    text = SMOKE.read_text()
    assert "8082" in text
    assert "8026" in text
    assert "nfr7.pdf" in text
    assert "needs_email_confirmation" in text or "confirm" in text
    assert "SMOKE_XAI_KEY" in text
    assert "OPENAI_API_KEY" not in text


def test_uat_readme_waits_not_arpw() -> None:
    readme = (ROOT / "UAT" / "README.md").read_text()
    assert "8082" in readme
    assert "1_260_000" in readme or "1260000" in readme
    assert "180s upload" not in readme.split("Do **not**")[1][:200] or "Do **not** copy ARPW" in readme
    assert ":3001" in readme
    runner = (ROOT / "UAT" / "run-literature-review.mjs").read_text()
    assert "1260000" in runner
    assert "localhost:8082" in runner
    assert "5173" not in runner
