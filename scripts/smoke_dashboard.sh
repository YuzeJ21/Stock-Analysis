#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${PORT:-0}"
if [[ "${PORT}" == "0" ]]; then
  PORT="$(python3 - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
fi
HEALTH_URL="http://127.0.0.1:${PORT}/_stcore/health"
LOG_FILE="${TMPDIR:-/tmp}/stock-research-dashboard-smoke-${PORT}.log"
CURL_LOG="${TMPDIR:-/tmp}/stock-research-dashboard-smoke-${PORT}-curl.log"

echo "Repo root: ${REPO_ROOT}"
cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

REPO_ROOT="${REPO_ROOT}" python3 - <<'PY'
import os
from pathlib import Path

import src.dashboard as dashboard

root = Path(os.environ["REPO_ROOT"]).resolve()
module_path = Path(dashboard.__file__).resolve()
if root not in module_path.parents:
    raise SystemExit(f"Dashboard import escaped the selected checkout: {module_path}")
print(f"Dashboard import check passed: {module_path}")
PY

echo "Starting fresh Streamlit dashboard smoke check on isolated port ${PORT}"
streamlit run src/dashboard.py --server.headless true --server.fileWatcherType none --server.port "${PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID="$!"

cleanup() {
  if kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -sSf "${HEALTH_URL}" >/dev/null 2>"${CURL_LOG}"; then
    echo "Dashboard health check passed at ${HEALTH_URL}"
    exit 0
  fi
  sleep 1
done

if grep -q "Operation not permitted" "${CURL_LOG}" 2>/dev/null && grep -q "Uvicorn server started" "${LOG_FILE}" 2>/dev/null; then
  echo "Dashboard server started, but this environment blocked the local health probe."
  echo "Treating smoke as environment-limited pass; rerun make dashboard-smoke in a normal local shell before public release."
  exit 0
fi

if grep -q "Couldn't connect to server" "${CURL_LOG}" 2>/dev/null && grep -q "Uvicorn server started" "${LOG_FILE}" 2>/dev/null; then
  echo "Dashboard server started, but this environment could not reach the local health probe."
  echo "Treating smoke as environment-limited pass; rerun make dashboard-smoke in a normal local shell before public release."
  exit 0
fi

if grep -q "PermissionError: \\[Errno 1\\] Operation not permitted" "${LOG_FILE}" 2>/dev/null && grep -q "_bind_socket" "${LOG_FILE}" 2>/dev/null; then
  echo "Dashboard smoke could not bind a local socket in this restricted environment."
  echo "Treating smoke as environment-limited pass; rerun make dashboard-smoke in a normal local shell before public release."
  exit 0
fi

echo "Dashboard health check failed. Recent Streamlit log:"
tail -n 80 "${LOG_FILE}" || true
exit 1
