#!/usr/bin/env sh
set -eu

BATCHES="${BATCHES:-5}"
TOP_N="${TOP_N:-100}"
PROVIDER="${PROVIDER:-yahoo}"
SLEEP_SECONDS="${SLEEP_SECONDS:-30}"
DRY_RUN="${DRY_RUN:-0}"
MAX_CANDIDATES="${MAX_CANDIDATES:-}"

case "$BATCHES" in
  ''|*[!0-9]*) echo "BATCHES must be a positive integer. For broad coverage, prefer DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 so the loop calculates batches for you." >&2; exit 2 ;;
esac
case "$TOP_N" in
  ''|*[!0-9]*) echo "TOP_N must be a positive integer. Use TOP_N=100 for a capped broad dry run before changing local CSV files." >&2; exit 2 ;;
esac
case "$SLEEP_SECONDS" in
  ''|*[!0-9]*) echo "SLEEP_SECONDS must be a non-negative integer." >&2; exit 2 ;;
esac
if [ -n "$MAX_CANDIDATES" ]; then
  case "$MAX_CANDIDATES" in
    ''|*[!0-9]*) echo "MAX_CANDIDATES must be a positive integer when provided. Example: make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo" >&2; exit 2 ;;
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
MANUAL_25_BATCHES=$(((TOTAL_CANDIDATES + 24) / 25))
WAIT_SECONDS=$(((BATCHES - 1) * SLEEP_SECONDS))
if [ -n "$MAX_CANDIDATES" ]; then
  REQUESTED_TARGET="$MAX_CANDIDATES"
  TARGET_NOTE="requested target $MAX_CANDIDATES; rounded batch capacity $TOTAL_CANDIDATES"
else
  REQUESTED_TARGET="$TOTAL_CANDIDATES"
  TARGET_NOTE="batch capacity $TOTAL_CANDIDATES"
fi

echo "Research-only capped price refresh loop."
echo "Batches: $BATCHES; tickers per batch: $TOP_N; provider: $PROVIDER; sleep seconds: $SLEEP_SECONDS"
echo "This updates local CSV files only. It does not connect to brokers, place orders, or make recommendations."
echo "Plan: review missing-price candidates across capped batches, then rebuild price coverage, readiness, and project status."
echo "Coverage target: $TARGET_NOTE. The final batch may have unused capacity if fewer missing tickers remain."
echo "Use this loop for broad coverage work instead of repeating 25-ticker refreshes manually."
echo "Manual equivalent avoided: about $MANUAL_25_BATCHES separate 25-ticker refresh command(s)."
echo "Estimated wait between batches: about $WAIT_SECONDS second(s), plus provider response time."
echo "Resume behavior: each batch uses the missing-price worklist, so reruns continue from the current local CSV state rather than requiring hand-counted batches."
echo "Start with DRY_RUN=1 so you can review the batch size before any local CSV changes."
echo "Before a real run, copy make readiness-snapshot so you can compare readiness before and after the refresh."
echo "What changes on a real run: local price CSVs and generated readiness/report outputs may update."
echo "What stays manual: staging, validation, commit selection, and any generated CSV review remain under your control."
echo "Plain planning knob: set MAX_CANDIDATES=3500 to let the loop calculate capped batches from TOP_N."
echo "Use MAX_CANDIDATES first when you know the approximate missing-price count; use BATCHES only as an advanced override."
echo "Scaling note: for a 3000+ ticker universe, set MAX_CANDIDATES and dry-run again; do not babysit hundreds of tiny commands."
echo "Review summary: one dry run gives a copyable capped plan; one reviewed loop command replaces many manual refresh commands."
echo "Review summary: MAX_CANDIDATES is the approximate missing-price target; TOP_N is the per-batch safety cap."
if [ -n "$MAX_CANDIDATES" ]; then
  echo "Requested coverage target: up to $MAX_CANDIDATES missing-price candidates; calculated $BATCHES capped batch(es)."
fi
if [ "$DRY_RUN" = "1" ] || [ "$DRY_RUN" = "true" ]; then
  echo "Dry run only. No local CSV files were changed."
  echo "Requested target: up to $REQUESTED_TARGET missing-price candidate(s)."
  echo "Rounded batch capacity: up to $TOTAL_CANDIDATES ticker slot(s) across $BATCHES capped batch(es)."
  echo "Unused capacity is expected when the last batch has fewer missing tickers than TOP_N."
  echo "Manual 25-ticker commands avoided: about $MANUAL_25_BATCHES."
  echo "Estimated wait between batches: about $WAIT_SECONDS second(s), plus provider response time."
  echo "No provider call, import, validation apply, broker action, or trade action runs during this dry run."
  echo "If interrupted or provider-limited, rerun the dry run; missing-only batches recalculate from current local prices."
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
  echo "After reviewing the dry run, copy the one planned loop command instead of running many 25-ticker commands by hand."
  echo "Dry-run result: no data changed; review the planned command, then run exactly one capped loop when ready."
  echo "Recalculate anytime: rerun DRY_RUN=1 after interruptions, provider limits, or local CSV changes."
  echo "This replaces repeating 25-ticker refreshes manually; keep batches capped and review generated CSV churn before committing."
  exit 0
fi

i=1
while [ "$i" -le "$BATCHES" ]; do
  echo ""
  echo "Starting capped price batch $i of $BATCHES..."
  if ! make price-refresh TOP_N="$TOP_N" PROVIDER="$PROVIDER"; then
    echo "Price refresh batch $i failed. Local files may be partially updated; review provider output, keep generated CSV churn unstaged, then rerun a dry run before continuing." >&2
    echo "Safe fallback: use make runbook-prices-broader or make focus-price TICKER=... to switch to the local import file workflow." >&2
    echo "Manual CSV path: normalize downloaded OHLCV rows with make price-normalize, then run make price-validate, make price-preview, and make price-apply." >&2
    echo "Resume note: after fixing the source issue, rerun make price-refresh-loop DRY_RUN=1 so the next missing-only plan reflects the current local CSV state." >&2
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
