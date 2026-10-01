#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="vllm"
if [[ $# -gt 0 && "$1" != -* ]]; then SUITE="$1"; shift; fi
exec python3 "$ROOT/audit_isolation.py" \
  --root "$ROOT/$SUITE" --feedback scalar \
  --counterpart "$ROOT/../bench_correct_feedback/$SUITE" "$@"
