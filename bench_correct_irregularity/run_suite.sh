#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  echo "usage: $0 SUITE [run_agent_pcvs options]" >&2
  exit 2
fi
SUITE="$1"
shift
SUITE_ROOT="$ROOT/$SUITE"
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  if [[ "${ARGS[$i]}" == "--root" && $((i + 1)) -lt ${#ARGS[@]} ]]; then
    SUITE_ROOT="${ARGS[$((i + 1))]}"
  elif [[ "${ARGS[$i]}" == --root=* ]]; then
    SUITE_ROOT="${ARGS[$i]#--root=}"
  fi
done
mkdir -p "$SUITE_ROOT"
exec 9>"$SUITE_ROOT/.runner.lock"
if ! flock -n 9; then
  echo "another scalar-feedback $SUITE runner is already active" >&2
  exit 1
fi
set -o pipefail
python3 "$ROOT/run_agent_pcvs.py" "$SUITE" "${ARGS[@]}" 2>&1 \
  | tee -a "$SUITE_ROOT/interactive-run.log"
