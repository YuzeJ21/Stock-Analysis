#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Repo root: ${REPO_ROOT}"
cd "${REPO_ROOT}"

make verify
make data-sources-check
make monthly
make track-record
make dashboard-smoke
