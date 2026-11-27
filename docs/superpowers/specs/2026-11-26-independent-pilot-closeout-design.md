# Independent pilot closeout design

## Intent

The research workflow has implemented replay, source checks and local private
access controls. Independent usage is still unverified. Existing pilot commands
print instructions and a CSV template; they cannot validate or summarize the
resulting sessions. Build a small operator tool to make that next milestone
measurable without claiming user validation from automated tests.

## Approach

Reuse the existing CSV and add provenance columns. A read-only standard-library
Python command validates and aggregates it. This is preferable to a second
feedback database, which duplicates the working log, or product telemetry,
which introduces collection, hosting and retention obligations before a pilot
exists. Implementation is authorized by the user's instruction to review,
choose the next goal and execute it; no additional design checkpoint is needed.

## Contract

- Add `reviewer_label`, `session_kind`, `delivery_kind`, `research_revision` and
  `session_phase` to the existing template. Labels are anonymous study-local
  tokens. Provenance is explicitly declared, not independently attested.
- `session_kind`: independent_researcher, owner_led, automated, fixture,
  screenshot. Only independent_researcher contributes usage metrics.
- `delivery_kind`: fictional_demo, local_research, hosted_private_pilot. Never
  pool these or different full 40-character Git revisions.
- `session_phase`: initial or return. Dates use ISO dates or timezone-aware ISO
  timestamps. A date-only record denotes the entire UTC day, not a known time.
  `--as-of` is an explicit ISO date; retention expires on that date.
- Reject malformed/oversized CSV, duplicate or missing headers and surplus
  cells with a generic error. Bound input to 2 MiB and 2,000 rows.
- Exclude unconsented, withdrawn, expired, future, duplicate-session-ID,
  non-independent or missing-provenance rows using fixed reason counters.
- Use each reviewer's earliest eligible initial session in each cohort. Later
  initial rows are explicitly counted as repeated initial attempts. Failed and
  incomplete initial attempts remain in the metric denominator. Invalid/missing
  score values are counted as missing, not interpreted as successful.
- Ambiguous first-attempt ordering retains one denominator with unknown scores
  and a visible ambiguous-reviewer count. Require provable temporal ordering for
  return visits. A dedicated input log covers one named exercise; other tasks
  remain separate even if delivery/revision match.
- Count returning reviewers only for an eligible, later, explicitly labelled
  return with a completed task in the same delivery/revision cohort.
- Report fixed score distributions, first-answer median with its own answered
  count, unassisted completion and observed return counts. Do not set a product
  maturity score or automatic approval threshold.
- Never emit identifiers, raw rows, feedback text or input paths. No file writes,
  provider requests, telemetry, readiness changes or automatic deletion.
- Argument errors use the same fixed private error. Make passes paths as literal
  data, not executable shell/Make text. Initialize new logs in fresh private
  directories; migrate known provenance without replacing existing logs.
- CLI: `python3 -m src.pilot_feedback --input FILE --as-of YYYY-MM-DD [--json]`.
  Add `make pilot-feedback-summary INPUT=FILE AS_OF=YYYY-MM-DD`.
- Update the current reviewer task to exercise company research, source trace,
  notes, saved evidence, Monitor and exact replay. Keep older optional tasks
  available as separately scoped legacy/saved-model checks.

## Verification and limits

Test the real CSV reader, aggregation and CLI against constructed mixed sessions,
including failure-inclusive counts, withdrawn/expired rows, duplicate IDs,
cross-cohort return attempts, malformed numeric/enum values and free-text
redaction. Assert input bytes and working-directory contents are unchanged.
Run existing pilot contracts and the repository suite; report environment
failures separately. Actual people, hosted authentication, data permissions and
operated recovery remain external evidence, regardless of synthetic results.
