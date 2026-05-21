#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${PORT:-8501}"
HEALTH_URL="http://127.0.0.1:${PORT}/_stcore/health"
LOG_FILE="${TMPDIR:-/tmp}/stock-research-dashboard-smoke-${PORT}.log"

echo "Repo root: ${REPO_ROOT}"
cd "${REPO_ROOT}"

if curl -sSf "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "Dashboard already healthy at ${HEALTH_URL}"
  exit 0
fi

echo "Starting Streamlit dashboard smoke check on port ${PORT}"
streamlit run src/dashboard.py --server.headless true --server.port "${PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID="$!"

cleanup() {
  if kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -sSf "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "Dashboard health check passed at ${HEALTH_URL}"
    exit 0
  fi
  sleep 1
done

echo "Dashboard health check failed. Recent Streamlit log:"
tail -n 80 "${LOG_FILE}" || true
exit 1
