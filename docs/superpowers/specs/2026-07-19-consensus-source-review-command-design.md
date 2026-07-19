# Consensus Source Review Command Design

## Purpose

The repository can classify consensus-provider availability and can validate in-memory source rows, but it has no supported command that joins those capabilities for a supplied reviewed CSV. Stage 2 therefore lacks a repeatable first gate between receiving a file and running prospective collection preview.

Add one read-only source-review command that loads a supplied CSV, requires an explicit provider identity and UTC review cutoff, calls the existing `validate_source_rows(...)` contract, and renders complete deterministic evidence. The command must not fetch, normalize, record, apply, rebuild readiness, create directories, or write generated artifacts.

This closes an operating gap only. It does not supply a dataset, approve rights, convert candidate context into point-in-time history, append a snapshot, or activate Earnings Nowcast.

## Approaches Considered

### Selected: explicit review mode in the existing source module

Extend `src.earnings_consensus_sources` with a `--review-csv` mode plus required `--provider` and `--as-of` arguments. Add `make earnings-consensus-source-review INPUT=<path> PROVIDER=<source_id> AS_OF=<timestamp>` as the stable entrypoint.

This keeps provider availability and source-row review in the same bounded module, reuses the existing validator directly, and preserves the current status command as the default behavior.

### Rejected: a new CLI module

A second module would isolate presentation but duplicate source-rights loading, argument handling, result serialization, and maintenance for a small read-only surface.

### Rejected: a documented inline Python invocation

An ad hoc snippet would not provide a tested operating gate, deterministic rendering, Make discoverability, or a stable reviewer handoff.

## Command Contract

The current command remains compatible:

```bash
make earnings-consensus-source-status
make earnings-consensus-source-status REVIEWED_CSV=<path> JSON=1
```

The new command is:

```bash
make earnings-consensus-source-review \
  INPUT=<reviewed.csv> \
  PROVIDER=<exact_source_id> \
  AS_OF=<UTC_timestamp>
```

`JSON=1` selects machine-readable output. The Make target passes only explicit values and never supplies a default input, provider, or cutoff.
It also sets `PYTHONDONTWRITEBYTECODE=1` so the read-only review cannot create local bytecode churn.

At the Python layer:

```bash
python3 -m src.earnings_consensus_sources \
  --review-csv <reviewed.csv> \
  --provider <exact_source_id> \
  --as-of <UTC_timestamp> \
  [--json]
```

When `--review-csv` is absent, `--provider` and `--as-of` are invalid rather than being ignored. When `--review-csv` is present, both are mandatory. This prevents partial invocations from appearing reviewed.

## Data Flow

1. Open the supplied CSV read-only with UTF-8 and newline-aware parsing.
2. Require a header row with non-blank, unique column names.
3. Reject rows containing more values than declared headers rather than silently dropping data.
4. Preserve header spelling and cell strings; do not infer, alias, normalize, or enrich evidence fields.
5. Pass the ordered row mappings, explicit provider, and explicit cutoff to `validate_source_rows(...)`.
6. Render the immutable `SourceValidationResult` in human or JSON form.

The existing validator remains the sole owner of history scope, required fields, timestamp ordering, fiscal/comparability validation, candidate versus historical routing, exact registry evidence, and row-level commercial scope decisions.

## Human Output

The human report starts with explicit boundaries and then prints stable summary fields:

- provider and normalized review cutoff;
- technical state;
- accepted and rejected row counts;
- historical-reviewable and candidate-context counts;
- rights status and commercial approval;
- commercial-ready and commercial-review-required counts;
- aggregate commercial blockers;
- rejected row numbers and reasons;
- accepted row commercial reviews with required fields, missing fields, readiness, and blockers;
- `auto_apply=false` and the next gate.

Empty tuples render as `none`. Row evidence remains ordered by the original one-based CSV row position. Technical rejection and commercial review remain separate.

The next gate is collection preview only when the operator has separately reviewed the payload and the relevant evidence states. The command never claims that a reviewable row is collected, activated, forecast-ready, backtest-ready, or calibrated.

## JSON Output

JSON serializes the existing frozen result through `dataclasses.asdict` with stable indentation and key ordering. No additional permissive or computed approval field is added. Tuple values become JSON arrays through the standard encoder.

## Exit And Error Behavior

- A readable CSV and valid invocation return exit code `0` after rendering the complete result, including `still_blocked`, candidate-only, rejected-row, or commercial-review-required states. The command is a review surface, not an automatic activation gate.
- Missing review arguments are parser errors and return nonzero.
- Missing, unreadable, or directory input paths return nonzero with a concise source-review error.
- Missing, blank, or duplicate headers return nonzero.
- Extra undeclared row values return nonzero.
- An invalid cutoff returns nonzero through the existing cutoff parser.
- A valid empty file with headers produces a truthful `still_blocked` result with zero accepted rows; it does not become an invocation error.

No error path creates an output file, directory, ledger, readiness artifact, bytecode artifact, or partial mutation.

## Testing

Test-first coverage will prove:

1. a reviewed historical fixture renders accepted, historical-reviewable, cutoff, rights, metric scope, and `auto_apply=false` evidence;
2. candidate-only input remains candidate context;
3. mixed valid/rejected rows preserve original row numbers and rejection reasons;
4. commercial rights and populated Revenue/EPS field scope remain independent;
5. JSON matches the existing result contract;
6. missing provider or cutoff fails explicitly;
7. missing input, missing headers, duplicate headers, and extra values fail without writes;
8. the existing status command remains byte-for-byte compatible for its current tested cases;
9. the Make target passes `INPUT`, `PROVIDER`, `AS_OF`, and optional `JSON` to the module without defaults;
10. review mode leaves the input byte-identical and creates no sibling or repository artifacts.

## Documentation And Product Boundary

Update the roadmap, Earnings Nowcast pilot, data strategy, methodology, provenance contract, and continuation prompt. Document the source-review command as the first non-writing Stage 2 gate before collection preview.

The command proves only local contract evaluation of supplied rows. It cannot prove provider entitlement, payload correctness, publication availability, source-reference durability, commercial rights beyond checked-in metadata, historical depth, collection, readiness, backtesting, calibration, hosted operation, reviewer adoption, commercial demand, or market validation.

## Completion Criteria

- One supported read-only command reviews a supplied consensus CSV through the existing validator.
- Existing provider-status behavior remains compatible.
- Invocation, CSV-shape, technical, temporal, commercial-rights, and metric-scope evidence fail closed without being conflated.
- No provider call, canonical mutation, consensus append, readiness rebuild, generated CSV/JSON/report/sample-report/screenshot/timing output, or bytecode churn occurs.
- Focused and full verification plus all required non-writing product and hygiene gates pass.
