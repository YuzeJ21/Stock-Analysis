# Proof Workflow Correction Design

## Goal

Make the short price-history workflow truthful and finite: show only executable
work by default, preserve reviewed source limits as evidence, and prevent
one-ticker commit/push loops from becoming the default operating model.

## Scope

- Keep `ROADMAP.md` as the single active roadmap.
- Convert the next-stage roadmap and continuity prompt into short pointers to
  the authoritative roadmap and current read-only status commands.
- Split price-history reporting into momentum-not-ready, unreviewed
  preferred-history, and reviewed source-limited counts.
- Keep reviewed source-limited names out of the default executable queue.
- Add a read-only batch-closeout plan for grouped unchanged source-limit
  outcomes. It must not refresh data, write proof rows, stage, commit, or push.
- Document stop rules for no readiness movement, repeated identical provider
  outcomes, and batched reviewed commits.

## Non-goals

- No provider refresh, data import, readiness rebuild, or coverage expansion.
- No change to source provenance, readiness thresholds, or research-only
  guardrails.
- No automatic proof recording, staging, committing, or pushing.

## Design

### Queue states

`price_history_proof_queue` will continue to derive all short-history rows from
the onboarding payload and proof ledger. It will expose a summary object with:

- `momentum_not_ready_count`: tickers without usable momentum history.
- `unreviewed_preferred_history_count`: current short-history rows without a
  non-actionable reviewed proof result.
- `reviewed_source_limited_count`: current short-history rows whose latest
  relevant proof result is `still_blocked`, `skipped`, or `excluded`.

The default rendered queue contains only the unreviewed set. `--include-reviewed`
adds the reviewed source-limited rows for audit visibility, but they retain a
wait-only next action and are never counted as executable.

### Batch closeout

A new read-only command will select reviewed source-limited price-history rows
and print one grouped proof-record scaffold. The scaffold includes the selected
ticker list and the shared stop reason, but does not call the proof recorder.
It exists so an operator can intentionally review one coherent batch and make
at most one proof-ledger commit and push decision for that batch.

### Runtime stop rules

The command and roadmap wording will state:

1. Stop the price-history run when a refresh/rebuild produces no readiness
   movement for the reviewed scope.
2. Stop retrying a provider path after the same source-limited outcome is
   already recorded for that ticker unless source behavior or verified OHLCV
   evidence changes.
3. Collect compatible outcomes into a reviewed batch; never commit or push one
   proof row per ticker by default.
4. Pivot to the next roadmap item after the executable queue is empty.

## Tests

- Default queue excludes reviewed non-actionable rows.
- `--include-reviewed` keeps reviewed rows visible with wait-only actions.
- Summary counts distinguish the three state groups.
- Batch-closeout output is read-only, uses grouped tickers, and states that it
  does not record, stage, commit, or push.
- Public docs reference existing Make targets and name `ROADMAP.md` as the
  authority.

## Verification

Run the focused queue, project-status, and launcher tests; the full test suite;
the public and pilot gates; hygiene; and whitespace validation. Stage only
intentional code, docs, and test files after every gate passes.
