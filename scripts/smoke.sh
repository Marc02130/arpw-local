#!/usr/bin/env bash
# Smoke: health → register → confirm (Mailpit) → login → paper → upload fixture → retrieve.
# Generate is skipped unless SMOKE_XAI_KEY or UAT/.uat-grok-key is a live xai- secret (exit 2).
# Prefer SMOKE_BASE_URL=http://localhost:8082 (PUBLIC_ORIGINS lists localhost, not 127.0.0.1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BASE="${SMOKE_BASE_URL:-http://127.0.0.1:8082}"
MAILPIT="${SMOKE_MAILPIT_URL:-http://127.0.0.1:8026}"
FIXTURE="$ROOT/tests/fixtures/nfr7.pdf"

json_get() {
  python3 -c "import json,sys; print(json.load(sys.stdin)$1)"
}

live_xai() {
  local key="${1:-}"
  case "$key" in
    "" | xai-not-set | xai-test*) return 1 ;;
    xai-*) return 0 ;;
    *) return 1 ;;
  esac
}

CHAT_KEY="${SMOKE_XAI_KEY:-}"
if [[ -z "$CHAT_KEY" && -f "$ROOT/UAT/.uat-grok-key" ]]; then
  CHAT_KEY="$(tr -d '[:space:]' < "$ROOT/UAT/.uat-grok-key")"
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "missing fixture: $FIXTURE" >&2
  exit 1
fi

COOKIE="$(mktemp)"
trap 'rm -f "$COOKIE"' EXIT

echo "== health =="
HEALTH="$(curl -fsS "$BASE/api/health")"
echo "$HEALTH" | grep -q '"status":"ok"' || { echo "health failed: $HEALTH" >&2; exit 1; }

EMAIL="smoke-$(date +%s)@example.com"
PASSWORD="correct-horse-battery"

echo "== register $EMAIL =="
REG="$(curl -fsS -c "$COOKIE" -b "$COOKIE" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Smoke User\"}" \
  "$BASE/api/auth/register")"
echo "$REG" | json_get "['needs_email_confirmation']" | grep -q True || \
  echo "$REG" | grep -q 'needs_email_confirmation' || { echo "register failed: $REG" >&2; exit 1; }

echo "== confirm via Mailpit =="
python3 - "$MAILPIT" "$EMAIL" "$COOKIE" <<'PY'
import json, sys, time, urllib.request
mailpit, email, cookie = sys.argv[1], sys.argv[2], sys.argv[3]
link = None
for _ in range(20):
    req = urllib.request.Request(mailpit.rstrip("/") + "/api/v1/messages")
    with urllib.request.urlopen(req, timeout=5) as res:
        data = json.load(res)
    messages = data.get("messages") or data if isinstance(data, list) else data.get("messages") or []
    for msg in messages:
        to = json.dumps(msg)
        if email.split("@")[0] in to or email in to:
            mid = msg.get("ID") or msg.get("id")
            with urllib.request.urlopen(mailpit.rstrip("/") + f"/api/v1/message/{mid}", timeout=5) as res:
                body = json.load(res)
            text = json.dumps(body)
            import re
            found = re.search(r"http://localhost:8082/api/auth/confirm\?token=[^\"\\\s]+", text)
            if found:
                link = found.group(0).replace("\\u0026", "&")
                break
    if link:
        break
    time.sleep(0.5)
if not link:
    sys.exit("no confirm link in Mailpit")
req = urllib.request.Request(link)
# follow redirects; do not require cookie for GET confirm
urllib.request.urlopen(req, timeout=10).read()
print("confirmed")
PY

echo "== login =="
curl -fsS -c "$COOKIE" -b "$COOKIE" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  "$BASE/api/auth/login" >/dev/null

echo "== create paper =="
PAPER="$(curl -fsS -c "$COOKIE" -b "$COOKIE" -H "Content-Type: application/json" \
  -d '{"title":"smoke","paper_type":"Literature Review"}' \
  "$BASE/api/papers")"
PID="$(echo "$PAPER" | json_get "['paper_id']")"
[[ -n "$PID" ]] || { echo "paper failed: $PAPER" >&2; exit 1; }

echo "== upload nfr7.pdf =="
UP="$(curl -fsS -c "$COOKIE" -b "$COOKIE" \
  -F "file=@${FIXTURE};type=application/pdf" \
  -F "source_role=literature" \
  "$BASE/api/references")"
STATUS="$(echo "$UP" | json_get "['status']")"
MODEL="$(echo "$UP" | json_get "['embedding_model']")"
[[ "$STATUS" == "ready" ]] || { echo "upload not ready: $UP" >&2; exit 1; }
echo "$MODEL" | grep -q MiniLM || { echo "expected MiniLM embedding_model: $UP" >&2; exit 1; }

echo "== retrieve nfr7probe =="
RET="$(curl -fsS -c "$COOKIE" -b "$COOKIE" -H "Content-Type: application/json" \
  -d '{"research_prompt":"nfr7probe","paper_type":"Literature Review","sections":["Literature Review"]}' \
  "$BASE/api/papers/${PID}/retrieve")"
echo "$RET" | grep -q nfr7probe || { echo "expected nfr7probe in retrieve: $RET" >&2; exit 1; }

if ! live_xai "$CHAT_KEY"; then
  echo "smoke ok (retrieve). Set SMOKE_XAI_KEY or UAT/.uat-grok-key (xai-...) to exercise generate."
  exit 2
fi

echo "== save xAI key =="
curl -fsS -c "$COOKIE" -b "$COOKIE" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json,sys; print(json.dumps({'xai_api_key':sys.argv[1],'chat_provider':'xai'}))" "$CHAT_KEY")" \
  "$BASE/api/settings/llm" >/dev/null

echo "smoke ok (key saved; generate is the literature-review UAT)"
exit 0
