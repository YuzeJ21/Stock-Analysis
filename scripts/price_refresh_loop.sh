#!/usr/bin/env sh
set -eu

BATCHES="${BATCHES:-5}"
TOP_N="${TOP_N:-100}"
PROVIDER="${PROVIDER:-yahoo}"
SLEEP_SECONDS="${SLEEP_SECONDS:-30}"
DRY_RUN="${DRY_RUN:-0}"
MAX_CANDIDATES="${MAX_CANDIDATES:-}"

case "$BATCHES" in
  ''|*[!0-9]*) echo "BATCHES must be a positive integer." >&2; exit 2 ;;
esac
case "$TOP_N" in
  ''|*[!0-9]*) echo "TOP_N must be a positive integer." >&2; exit 2 ;;
esac
case "$SLEEP_SECONDS" in
  ''|*[!0-9]*) echo "SLEEP_SECONDS must be a non-negative integer." >&2; exit 2 ;;
esac
if [ -n "$MAX_CANDIDATES" ]; then
  case "$MAX_CANDIDATES" in
    ''|*[!0-9]*) echo "MAX_CANDIDATES must be a positive integer when provided." >&2; exit 2 ;;
  esac
fi

if [ "$BATCHES" -lt 1 ] || [ "$TOP_N" -lt 1 ]; then
  echo "BATCHES and TOP_N must be at least 1." >&2
  exit 2
fi
if [ -n "$MAX_CANDIDATES" ] && [ "$MAX_CANDIDATES" -lt 1 ]; then
  echo "MAX_CANDIDATES must be at least 1 when provided." >&2
  exit 2
fi

if [ -n "$MAX_CANDIDATES" ]; then
  BATCHES=$(((MAX_CANDIDATES + TOP_N - 1) / TOP_N))
fi

TOTAL_CANDIDATES=$((BATCHES * TOP_N))

echo "Research-only capped price refresh loop."
echo "Batches: $BATCHES; tickers per batch: $TOP_N; provider: $PROVIDER; sleep seconds: $SLEEP_SECONDS"
echo "This updates local CSV files only. It does not connect to brokers, place orders, or make recommendations."
echo "Plan: review up to $TOTAL_CANDIDATES missing-price candidates across capped batches, then rebuild price coverage, readiness, and project status."
echo "Use this loop for broad coverage work instead of repeating 25-ticker refreshes manually."
echo "Start with DRY_RUN=1 so you can review the batch size before any local CSV changes."
echo "Before a real run, copy make readiness-snapshot so you can compare readiness before and after the refresh."
echo "Plain planning knob: set MAX_CANDIDATES=3500 to let the loop calculate capped batches from TOP_N."
echo "Scaling note: for a 3000+ ticker universe, set MAX_CANDIDATES and dry-run again; do not babysit hundreds of tiny commands."
if [ -n "$MAX_CANDIDATES" ]; then
  echo "Requested coverage target: up to $MAX_CANDIDATES missing-price candidates; calculated $BATCHES capped batch(es)."
fi
if [ "$DRY_RUN" = "1" ] || [ "$DRY_RUN" = "true" ]; then
  echo "Dry run only. No local CSV files were changed."
  echo "Planned coverage: up to $TOTAL_CANDIDATES missing-price candidates across $BATCHES capped batch(es)."
  if [ -n "$MAX_CANDIDATES" ]; then
    echo "Planned loop command: make price-refresh-loop MAX_CANDIDATES=$MAX_CANDIDATES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS"
  else
    echo "Planned loop command: make price-refresh-loop BATCHES=$BATCHES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS"
  fi
  echo "Each capped batch would run: make price-refresh TOP_N=$TOP_N PROVIDER=$PROVIDER"
  echo "Post-loop commands would be: make price-coverage TOP_N=25; make readiness; make project-status"
  echo "Snapshot command before a real run: make readiness-snapshot"
  echo "Hygiene command after a real run: make diff-hygiene"
  echo "Recommended next sequence:"
  echo "  1. make readiness-snapshot"
  if [ -n "$MAX_CANDIDATES" ]; then
    echo "  2. make price-refresh-loop MAX_CANDIDATES=$MAX_CANDIDATES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS"
  else
    echo "  2. make price-refresh-loop BATCHES=$BATCHES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS"
  fi
  echo "  3. make diff-hygiene"
  echo "  4. make stock-report-md TICKER=NVDA or reopen the dashboard to review the local result"
  echo "If you want broader coverage, set MAX_CANDIDATES first while keeping TOP_N capped, then dry-run again."
  echo "Example broad dry run: make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=$PROVIDER"
  echo "Advanced alternative: make price-refresh-loop DRY_RUN=1 BATCHES=30 TOP_N=100 PROVIDER=$PROVIDER"
  echo "This replaces repeating 25-ticker refreshes manually; keep batches capped and review generated CSV churn before committing."
  exit 0
fi

i=1
while [ "$i" -le "$BATCHES" ]; do
  echo ""
  echo "Starting capped price batch $i of $BATCHES..."
  if ! make price-refresh TOP_N="$TOP_N" PROVIDER="$PROVIDER"; then
    echo "Price refresh batch $i failed. Local files may be partially updated; review provider output, keep generated CSV churn unstaged, then rerun a dry run before continuing." >&2
    echo "Safe fallback: use make runbook-prices-broader or make focus-price TICKER=... to switch to the local import draft workflow." >&2
    echo "Manual CSV path: normalize downloaded OHLCV rows with make price-normalize, then run make price-validate, make price-preview, and make price-apply." >&2
    exit 1
  fi
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
echo "Next: run make diff-hygiene before staging so refreshed generated CSV churn stays local unless intentionally reviewed."
