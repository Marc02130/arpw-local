#!/usr/bin/env python3
"""Operator dogfood against the live Compose app (:8082).

Walks signup → confirm → key → upload nfr7 → retrieve → pin → interrogate →
outline → generate → library. Requires a live xai- key (DOGFOOD_XAI_KEY or
UAT/.uat-grok-key). Exit 2 if the key is missing.

  docker compose up --build
  ./scripts/dogfood.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("DOGFOOD_BASE_URL", "http://127.0.0.1:8082").rstrip("/")
MAILPIT = os.environ.get("DOGFOOD_MAILPIT_URL", "http://127.0.0.1:8026").rstrip("/")
FIXTURE = ROOT / "tests" / "fixtures" / "nfr7.pdf"
KEY_FILE = ROOT / "UAT" / ".uat-grok-key"
PROMPT = (
    "Synthesize a short literature review from the uploaded fixture only. "
    "Cite only retrieved [S#] ids. Do not invent studies."
)

COOKIES = CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIES))


def log(msg: str) -> None:
    print(f"== {msg} ==", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def live_xai(key: str) -> bool:
    key = key.strip()
    if not key or key in {"xai-not-set", "xai-test"}:
        return False
    if key.startswith("/") or key.startswith("./") or "\\" in key:
        return False
    return key.startswith("xai-")


def load_key() -> str:
    env = os.environ.get("DOGFOOD_XAI_KEY") or os.environ.get("SMOKE_XAI_KEY") or ""
    if env.strip():
        return env.strip()
    if KEY_FILE.is_file():
        return KEY_FILE.read_text().strip()
    return ""


def request(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60,
) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with OPENER.open(req, timeout=timeout) as res:
            return res.status, res.read().decode()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        return exc.code, body


def json_req(method: str, path: str, payload: dict | None = None, timeout: float = 60) -> tuple[int, dict | list | str]:
    headers = {"Content-Type": "application/json", "Origin": BASE}
    data = None if payload is None else json.dumps(payload).encode()
    status, text = request(method, BASE + path, data=data, headers=headers, timeout=timeout)
    try:
        return status, json.loads(text)
    except json.JSONDecodeError:
        return status, text


def confirm_from_mailpit(email: str) -> None:
    local = email.split("@")[0]
    link = None
    for _ in range(30):
        status, raw = request("GET", f"{MAILPIT}/api/v1/messages", timeout=5)
        if status != 200:
            time.sleep(0.5)
            continue
        data = json.loads(raw)
        messages = data.get("messages") or []
        for msg in messages:
            if local not in json.dumps(msg) and email not in json.dumps(msg):
                continue
            mid = msg.get("ID") or msg.get("id")
            _, body = request("GET", f"{MAILPIT}/api/v1/message/{mid}", timeout=5)
            found = re.search(r"http://localhost:8082/api/auth/confirm\?token=[^\"\\\s]+", body)
            if found:
                link = found.group(0).replace("\\u0026", "&")
                break
        if link:
            break
        time.sleep(0.5)
    if not link:
        die("no confirm link in Mailpit")
    status, _ = request("GET", link, timeout=15)
    if status not in {200, 302}:
        die(f"confirm GET failed: {status}")
    log("confirmed")


def main() -> None:
    key = load_key()
    if not live_xai(key):
        die(
            "dogfood requires a live xai- key: export DOGFOOD_XAI_KEY=xai-... "
            "or write UAT/.uat-grok-key",
            2,
        )
    if not FIXTURE.is_file():
        die(f"missing fixture {FIXTURE}")

    log("health")
    status, body = json_req("GET", "/api/health")
    if status != 200 or (isinstance(body, dict) and body.get("status") != "ok"):
        die(f"health failed: {status} {body}")

    email = f"dogfood-{int(time.time())}@example.com"
    password = "correct-horse-battery"
    log(f"register {email}")
    status, body = json_req(
        "POST",
        "/api/auth/register",
        {"email": email, "password": password, "full_name": "Dogfood User"},
    )
    if status != 201:
        die(f"register failed: {status} {body}")

    log("confirm via Mailpit")
    confirm_from_mailpit(email)

    log("login")
    status, body = json_req("POST", "/api/auth/login", {"email": email, "password": password})
    if status != 200:
        die(f"login failed: {status} {body}")

    log("save xAI key")
    status, body = json_req(
        "PUT",
        "/api/settings/llm",
        {"xai_api_key": key, "chat_provider": "xai"},
    )
    if status != 200:
        die(f"settings failed: {status} {body}")

    log("upload nfr7.pdf")
    boundary = "----DogfoodBoundary"
    raw = FIXTURE.read_bytes()
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"source_role\"\r\n\r\nliterature\r\n".encode(),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"nfr7.pdf\"\r\nContent-Type: application/pdf\r\n\r\n"
        ).encode()
        + raw
        + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    status, text = request(
        "POST",
        BASE + "/api/references",
        data=b"".join(parts),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Origin": BASE,
        },
        timeout=180,
    )
    up = json.loads(text)
    if status != 201 or up.get("status") != "ready":
        die(f"upload not ready: {status} {up}")
    if "MiniLM" not in (up.get("embedding_model") or ""):
        die(f"expected MiniLM: {up}")

    log("create Literature Review paper")
    status, paper = json_req(
        "POST",
        "/api/papers",
        {"title": "Dogfood literature review", "paper_type": "Literature Review"},
    )
    if status != 201:
        die(f"paper failed: {status} {paper}")
    pid = paper["paper_id"]
    sections = [
        "Abstract",
        "Introduction",
        "Literature Review",
        "Discussion",
        "Conclusion",
        "References",
    ]
    json_req("PATCH", f"/api/papers/{pid}", {"sections": sections, "research_prompt": PROMPT})

    log("retrieve nfr7probe")
    status, ret = json_req(
        "POST",
        f"/api/papers/{pid}/retrieve",
        {
            "research_prompt": "nfr7probe " + PROMPT,
            "paper_type": "Literature Review",
            "sections": ["Literature Review", "Introduction"],
        },
        timeout=120,
    )
    if status != 200:
        die(f"retrieve failed: {status} {ret}")
    passages = ret.get("passages") or []
    blob = " ".join(p.get("chunk_text") or "" for p in passages)
    if "nfr7probe" not in blob:
        die(f"expected nfr7probe in retrieve: {ret}")
    if any(p.get("source_role") == "primary" for p in passages):
        die("Literature Review retrieve must not return primary")

    first = passages[0]
    log("pin first passage")
    status, pin = json_req(
        "POST",
        f"/api/papers/{pid}/pins",
        {"vector_id": first["vector_id"], "file_id": first["file_id"]},
    )
    if status != 201:
        die(f"pin failed: {status} {pin}")

    log("interrogate")
    status, asked = json_req(
        "POST",
        f"/api/papers/{pid}/interrogation",
        {"question": "What is nfr7probe?", "sources": ["literature"]},
        timeout=180,
    )
    if status != 200:
        die(f"interrogate failed: {status} {asked}")
    if not asked.get("answer"):
        die(f"empty interrogate answer: {asked}")

    log("outline")
    status, outlined = json_req(
        "POST",
        f"/api/papers/{pid}/outline",
        {"paper_type": "Literature Review", "sections": sections, "research_prompt": PROMPT},
        timeout=180,
    )
    if status != 200:
        die(f"outline failed: {status} {outlined}")

    log("generate (up to 2100s)")
    status, gen = json_req(
        "POST",
        f"/api/papers/{pid}/generate",
        {
            "paper_type": "Literature Review",
            "sections": sections,
            "research_prompt": PROMPT,
            "citation_style": "APA",
            "output_format": "markdown",
        },
        timeout=2100,
    )
    if status != 200:
        die(f"generate failed: {status} {gen}")
    paper_out = gen.get("paper") or {}
    if paper_out.get("paper_type") != "Literature Review":
        die(f"generate overwrote paper_type: {paper_out}")
    content = paper_out.get("content") or ""
    if "## Abstract" not in content:
        die("generate missing Abstract heading")
    if "[S99]" in content:
        die("unknown [S99] survived generate")
    if "disclaimer" not in gen or "human review" not in gen["disclaimer"].lower():
        die("missing disclaimer")

    log("library list + continue shape")
    status, listed = json_req("GET", "/api/papers")
    if status != 200 or not any(p.get("paper_id") == pid for p in listed):
        die(f"library missing paper: {listed}")
    status, again = json_req("GET", f"/api/papers/{pid}")
    if status != 200 or again.get("paper_type") != "Literature Review":
        die(f"continue restored wrong type: {again}")

    log("export markdown + word")
    md = f"# {again['title']}\n\n{again['content']}\n\n---\n{gen['disclaimer']}\n"
    if "human review" not in md.lower():
        die("markdown export missing disclaimer")
    status, _docx = request("GET", f"{BASE}/api/papers/{pid}/export.docx", timeout=30)
    if status != 200:
        die(f"docx export failed: {status}")

    print("dogfood ok")
    print(f"  email={email}")
    print(f"  paper={pid}")
    print(f"  app={BASE}")


if __name__ == "__main__":
    main()
