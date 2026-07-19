# Readiness Impact Preview Design

## Purpose

The saved readiness snapshot is truthfully stale because declared source dates are newer than its build time. The repository's current unblock command, `make readiness`, rewrites multiple CSV reports. The active continuation contract explicitly forbids generating that churn without separate approval.

Add a deterministic, read-only preview that computes the proposed readiness state in memory, compares it with the saved snapshot, and prints the expected impact without creating, modifying, or deleting any file.

## Selected Approach

Thread an explicit no-write option through the existing universe and readiness builders, then add a small preview module and Make target.

This approach is preferred because it executes the same readiness logic that a later reviewed rebuild would use. A temporary-directory rebuild was rejected because it still generates CSV files. A metadata-only freshness explanation was rejected because it cannot reveal which readiness states would change.

## Architecture

### Pure universe preparation

`ensure_universe_files(..., write_outputs=True)` keeps its current default behavior. When `write_outputs=False`, it may construct or repair the master and active frames in memory, but it must not write canonical universe files.

`build_universe_coverage_report(..., write_output=True)` keeps its current default behavior. Its no-write mode calls the universe helper with `write_outputs=False` and returns the coverage frame without creating the reports directory or CSV.

### Pure readiness build

`build_ticker_readiness_report(..., write_outputs=True)` keeps its current default behavior. In no-write mode it:

- loads the same selected-profile inputs;
- calls only no-write universe preparation;
- builds the same report frames;
- returns all frames in memory;
- skips every report, compatibility-copy, and output write;
- creates no directories.

Default callers remain unchanged and continue writing their existing artifacts.

### Impact preview

A focused `src.readiness_preview` module will:

1. load the saved ticker-readiness report;
2. call `build_ticker_readiness_report(..., write_outputs=False)`;
3. compare only stable readiness fields, excluding volatile timestamps and explanatory text that does not change readiness;
4. report saved and proposed counts for overall state plus price, fundamentals, DCF, peer, earnings, and analyst-estimates readiness;
5. report capped changed tickers and changed stable fields;
6. state explicitly that the preview wrote no files and did not make readiness current.

The command is `make readiness-preview TOP_N=20`. It prints to stdout only. It has no output-path option and no JSON/file mode.

## Stable Comparison Contract

The preview compares:

- `overall_readiness_state`;
- `price_ready`;
- `momentum_ready`;
- `fundamentals_ready`;
- `dcf_ready`;
- `peer_ready`;
- `earnings_ready`;
- `analyst_estimates_ready`;
- `ready_features`;
- `partial_features`;
- `blocked_features`;
- `excluded_features`.

It does not compare `updated_at`, generated timestamps, command copy, source-status attempt times, or other volatile presentation fields.

## Failure Behavior

- Missing saved readiness: return `missing_saved_snapshot`; show that comparison is unavailable; do not write a replacement.
- Missing canonical inputs: preserve the readiness engine's current fail-closed result or error; do not create fallback files.
- In-memory build failure: return a non-zero CLI result with a concise error; leave the filesystem unchanged.
- No stable changes: report `no_readiness_changes`; stale freshness remains stale until a reviewed rebuild is intentionally run.
- Stable changes: report `changes_detected`; this is preview evidence only and does not authorize or perform a rebuild.

## Safety Boundaries

- No CSV, JSON, report, sample report, screenshot, timing output, or directory is created.
- No source row, readiness state, proof ledger, journal, consensus snapshot, valuation, catalyst, outcome, backtest, or calibration state is mutated.
- Candidate context cannot enter the build as trusted evidence.
- The preview does not prove data rights, source freshness, correctness, or pilot readiness.
- `make readiness` remains a separate intentional write action requiring generated-artifact review.
- Research-only language remains unchanged; the command provides no ranking, recommendation, forecast, probability, or transaction instruction.

## Testing

Test-first coverage will prove:

1. no-write universe preparation returns expected frames without creating canonical files;
2. no-write universe coverage creates no report directory or CSV;
3. no-write readiness returns the expected frames while a before/after filesystem manifest remains identical;
4. preview comparison ignores timestamp-only differences;
5. preview reports stable readiness changes and caps ticker detail;
6. missing saved readiness fails closed without writing;
7. the Make target and documentation preserve the no-artifact and no-unlock boundaries.

After focused tests, run the full repository, dashboard, Research render, public, commercial-beta, pilot, whitespace, and hygiene gates. The pilot verdict is expected to remain blocked by stale readiness because this slice intentionally does not rebuild it.

## Completion Criteria

- `make readiness-preview TOP_N=20` runs against the current repository without changing `git status` or any filesystem content.
- The command reports the saved-versus-proposed stable readiness impact.
- Existing write-mode behavior remains regression-tested and unchanged.
- No generated artifact is staged or committed.
- ROADMAP, data strategy, the continuation prompt, and draft PR #113 state that preview evidence is not a readiness rebuild or pilot unlock.
