#!/usr/bin/env sh
set -eu

BATCHES="${BATCHES:-5}"
TOP_N="${TOP_N:-100}"
PROVIDER="${PROVIDER:-yahoo}"
SLEEP_SECONDS="${SLEEP_SECONDS:-30}"
DRY_RUN="${DRY_RUN:-0}"

case "$BATCHES" in
  ''|*[!0-9]*) echo "BATCHES must be a positive integer." >&2; exit 2 ;;
esac
case "$TOP_N" in
  ''|*[!0-9]*) echo "TOP_N must be a positive integer." >&2; exit 2 ;;
esac
case "$SLEEP_SECONDS" in
  ''|*[!0-9]*) echo "SLEEP_SECONDS must be a non-negative integer." >&2; exit 2 ;;
esac

if [ "$BATCHES" -lt 1 ] || [ "$TOP_N" -lt 1 ]; then
  echo "BATCHES and TOP_N must be at least 1." >&2
  exit 2
fi

echo "Research-only capped price refresh loop."
echo "Batches: $BATCHES; tickers per batch: $TOP_N; provider: $PROVIDER; sleep seconds: $SLEEP_SECONDS"
echo "This updates local CSV files only. It does not connect to brokers, place orders, or make recommendations."
echo "Plan: run capped missing-price batches, then rebuild price coverage, readiness, and project status."
if [ "$DRY_RUN" = "1" ] || [ "$DRY_RUN" = "true" ]; then
  echo "Dry run only. No local CSV files were changed."
  echo "First batch command would be: make price-refresh TOP_N=$TOP_N PROVIDER=$PROVIDER"
  echo "Post-loop commands would be: make price-coverage TOP_N=25; make readiness; make project-status"
  exit 0
fi

i=1
while [ "$i" -le "$BATCHES" ]; do
  echo ""
  echo "Starting capped price batch $i of $BATCHES..."
  make price-refresh TOP_N="$TOP_N" PROVIDER="$PROVIDER"
  if [ "$i" -lt "$BATCHES" ] && [ "$SLEEP_SECONDS" -gt 0 ]; then
    echo "Sleeping $SLEEP_SECONDS seconds before the next capped batch..."
    sleep "$SLEEP_SECONDS"
  fi
  i=$((i + 1))
done

echo ""
echo "Rebuilding coverage, readiness, and project status after capped refresh loop..."
make price-coverage TOP_N=25
make readiness
make project-status
echo "Done. Review data/reports/ticker_readiness_report.csv and outputs/project_status_next_steps.csv for the actual readiness change."
