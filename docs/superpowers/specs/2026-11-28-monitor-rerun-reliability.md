# Monitor rerun reliability

The current full CI has one failure and 10,760 passes: the large TSM test can
find its company in Monitor but then reports unverified snapshots. A controlled
overlap reproduces this with the real compressed store. The test app scopes
process-global PROJECT_ROOT and socket patches to individual Streamlit runs.
An older interrupted run can undo those settings inside a newer run.

Keep the browser fixture's root and loopback-only socket guard stable for its
dedicated server process. Wrap the original socket functions, not another run's
wrapper. Do not change production storage, authorization or error handling.
The test-process owner restores state in the deterministic parent-process test;
the subprocess fixture ends its process for actual browser cleanup.

Acceptance: an older interrupted Monitor run cannot invalidate a newer run;
the latest observation and held revenue gap are rendered from the exact stored
context, bytes remain unchanged and external requests stay denied. The existing
desktop/phone save, idempotent save, Monitor and exact return assertions remain.
Run these cases in the early release gate as well as the full suite. No source
acquisition, snapshot retimestamping or readiness/valuation promotion is allowed.
