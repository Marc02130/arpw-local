#!/usr/bin/env bash
# Operator dogfood: live Compose walkthrough (signup → generate → library).
# Requires docker compose up and a live xai- key (DOGFOOD_XAI_KEY or UAT/.uat-grok-key).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/dogfood.py" "$@"
