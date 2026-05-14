#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Repo root: ${REPO_ROOT}"
cd "${REPO_ROOT}"

python3 -m pytest tests -q
python3 -m src.data_sources --check
python3 -m src.report_generator
python3 -m src.monthly_picks --generate --top-n 5
python3 -m src.track_record --monthly-picks
python3 -m src.stock_report --validate-local-data
