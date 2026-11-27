# Independent research pilot closeout — local release evidence

Reviewed November 26, 2026. Base: `709601485c6456275d779c58aedd6fbb55f39f6d`.

## Product review and delivered change

The company research, source trace, notes, saved context and Monitor workflow
already has local implementation evidence. Independent researcher completion,
repeat use, operated source permissions and intended-host controls remain open.
The previous pilot commands printed guidance but did not validate or summarize
the resulting session records; the generic exercises also needed a clearly
scoped current company task.

This slice adds `make pilot-feedback-summary`, reusing the existing working CSV.
It groups operator-declared independent sessions by tested revision and delivery
mode; preserves unsuccessful and incomplete first attempts; reports help,
comprehension, evidence tracing, friction, trust, performance and misuse scores;
and separates intent from provably later completed return visits. Ambiguous
initial chronology retains one denominator with unknown scores. No participant
identifiers, free text, input paths or raw records are printed. Inputs and source
eligibility remain unchanged.

The [next-goal prompt](goals/INDEPENDENT_RESEARCH_PILOT_GOAL.md),
[operator guide](PILOT_FEEDBACK_SUMMARY.md) and current reviewer task define the
scope. The guide initializes new logs in fresh private directories and explains
legacy migration without inventing provenance. Different exercises use separate
logs, even when revision and delivery labels match.

## Verification

- **145 tests passed** under `src.no_write_artifact_guard`, including all 50 new
  feedback cases, existing pilot feedback contracts, private-beta classification,
  snapshot persistence, company notes and workspace audit. The final run took
  8.69 seconds with one existing dateutil deprecation warning.
- The new cases were observed failing before implementation. They exercise real
  CSV input and CLI/Make execution, failure-inclusive denominators, consent,
  retention, duplication, date precision, cohort separation, malformed data,
  privacy, literal special-character filenames, bounded input, no transport and
  unchanged input bytes. All use constructed sessions, not actual reviewers.
- `make public-wording-check` passed, scanning 78 public files.
- `git diff --check` passed. All **89 tracked data/config/asset inputs** match the
  base bytes. The full protected data/output/asset manifests also match an
  untouched baseline checkout, including ignored paths and directory state.
- An independent code review found five important issues: ambiguous timestamp
  ordering, arbitrary tied-first-attempt selection, argument-error redaction,
  Make filename handling and safe working-log initialization. Each was addressed;
  code regressions were observed failing and then passing. Task separation and
  legacy migration were also clarified. No second review is claimed.

## Whole-suite limitation

The whole repository suite was attempted and interrupted at approximately 35%
after repeated errors/failures; it did **not** pass and did not produce a complete
failure inventory. Do not interpret the focused run as a full-suite result.

A fresh failure-limit run produced **242 passed, 1 error** before stopping at:

`tests/test_bank_peer_packet_browser.py::test_bank_packets_are_losslessly_retained_and_rechecked_without_promoting_pe[desktop]`

The setup calls `src.public_performance_gate._free_port()` and the sandbox denies
`socket.bind(('127.0.0.1', 0))` with `PermissionError: [Errno 1] Operation not
permitted`. The exact error reproduces on the untouched base revision. The other
failures in the interrupted broad run were not individually classified.

The installed environment is Streamlit 1.59.2 and Playwright 1.61.0; the project
declares 1.62.0 for both. Authlib is not installed. No dependency declarations or
test assertions were weakened to accommodate the environment. Re-run the full
release matrix with the declared dependencies and permitted local server/browser
execution before merging or declaring a release ready.

## Remaining evidence and implementation decisions

- The original checkout remains unchanged and behind GitHub. Native worktree
  creation was unavailable and its Git metadata was read-only, so implementation
  used a separate writable clone based on the verified GitHub commit.
- The user explicitly requested the next prompt and execution; implementation
  proceeded inline without another approval checkpoint.
- Reviewer labels and independence are operator declarations. The tool does not
  authenticate participants, establish target-persona fit, or verify source/host
  eligibility. Withdrawal follows the existing per-row contract. Incorrect
  operator declarations remain an external evidence risk.
- The 10–20 independent-reviewer target remains open. No reviewer was contacted,
  no real sessions were fabricated, and no hosting, credentials, source rights,
  paid data, canonical data or readiness state was changed.
- Operated private-pilot readiness remains false. This slice makes the next
  validation milestone executable; it does not complete that milestone or
  establish demand, retention, financial validity or commercial readiness.
