# Verified research journey design

The existing end-to-end tests exercise real calculation, persistence and UI
code using constructed transports. They currently run inside a broad CI suite;
missing browser support may skip cases. A separate fail-closed job will make the
complete company workflow observable without replacing the full engineering gate.

Reuse the existing self-service, exact Monitor return and provider-recovery
browser tests, plus their supporting financial, peer, snapshot and notes cases.
Alternatives were waiting only for the broad suite, which gives no separate
journey result, and duplicating the journey in a new test, which increases
maintenance without improving coverage. A small pytest observer will require
all six existing mandatory desktop/phone cases to collect and pass setup, call
and teardown. Every collected supporting case must also complete those phases.
Collection skips, deselection, xfail/XPASS, zero-code early exits with incomplete
evidence and missing phases fail the gate. Inherited `PYTEST_ADDOPTS`, optimized
Python and explicit xfail overrides cannot weaken evidence. A nonzero pytest
exit can never become success.

The verifier uses Python 3.11+ for standard-library TOML parsing; CI uses 3.12.
It checks declared Python/runtime/dev/workspace requirements and installed
Chromium before attempting a localhost server. The same validated executable is
selected for actual test launches through a scoped environment override. Explicit
candidate lists and normal unset-override browser discovery retain their scope.
An unavailable or
mismatched environment reports blocked with a nonzero exit, not a test pass.
The existing artifact guard wraps the command. No provider access, new external
service, canonical-data mutation or private-record migration is introduced.

Add `make research-journey-check`, and a separate parallel GitHub job using Python
3.12, `.[dev,workspace]`, and installed Playwright Chromium. Keep the current full
suite, smoke, wording and hygiene steps. Use the same workspace extra there.
The user explicitly requested this goal and execution; proceed inline using the
existing isolated checkout. Real-user, operated-host and source-rights evidence
remain outside this engineering result.
