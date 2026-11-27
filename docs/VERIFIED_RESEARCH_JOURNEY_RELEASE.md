# Verified research journey — release check

Reviewed November 26, 2026. This slice follows the independent-feedback closeout
and adds an independently reported engineering check for the existing research
workflow. It does not add financial coverage or establish actual pilot use.

## What the check runs

`make research-journey-check` executes existing production-backed tests with
constructed sources and disposable records:

| Mandatory case | Desktop/phone result required |
| --- | --- |
| Online-only self-service company research | Search, explicit research, financial trends, scenario, note preview/confirmation, snapshot save, Monitor, exact historical replay. |
| Online research round trip | Preserve the company, issuer, selected section and evidence on return from Monitor. |
| Provider failure and recovery | Withdraw an unavailable comparison, retain immutable saved evidence, recover on explicit retry and replay through Monitor. |

All six parametrized browser cases must collect once and complete setup, call
and teardown successfully. Every collected supporting case must do the same.
Collection skips, deselection, missing reports, xfail/XPASS, support failures and
zero-code early exits with incomplete evidence cannot pass. The runner rejects
inherited `PYTEST_ADDOPTS` and optimized Python rather than letting external
options weaken the check.

The release verifier requires Python 3.11+ for standard-library TOML support;
CI uses Python 3.12. Runtime, development and workspace dependencies are checked
against the current manifest. Preflight selects an installed, executable
Playwright Chromium and requires local-server capability. The browser helper
uses that same executable during the run through a scoped override, restored
afterward. Normal unset-override discovery and explicit candidate lists retain
their existing scope. A missing/invalid override never falls back silently.

The existing no-write guard wraps the entire command. Supporting cases cover
financial refresh, peer-source handling, snapshots, company notes and Workbench
integration. No source permission or saved-readiness gate is promoted.

## CI and result interpretation

The Commercial Research Beta workflow now runs `research-journey` separately
from `local-engineering-gate`. Both check out the PR head and install the declared
development/workspace extras. The journey job installs Playwright Chromium;
the existing full-suite, startup, render, wording, hygiene and whitespace steps
remain in the engineering job.

Use the [revision-specific CI checks](https://github.com/YuzeJ21/Stock-Analysis/actions)
for the actual result of each revision. A journey pass does not replace the full
suite, and this document is not an assertion that either remote job passed.
Both results need review before merging. Branch-protection settings were not
inspected or changed; creating a job alone does not enforce a merge rule.

## Local evidence

- **211 tests passed** under the protected-artifact guard in 12.43 seconds:
  30 new gate cases, the public performance/browser-selection tests, and existing
  financial, peer, snapshot, notes, Workbench and feedback cases. One existing
  dateutil deprecation warning remains.
- Gate policy tests execute real pytest subprocesses. They reproduce skipped
  collection, xfail/XPASS, deselection, optimized execution, inherited flags,
  setup/teardown errors, duplicate collection, collect-only and explicit zero
  exits after failed or unexecuted supporting tests.
- The six mandatory browser identities were collected successfully. They were
  **not executed locally**: the installed Streamlit and Playwright versions do
  not match the manifest, Authlib is missing and localhost/browser capabilities
  are sandbox-restricted. The real Make command reports `blocked`, exit code 2.
- A supplemental repository run reached 379 passes and one skip before
  `test_shared_demo_style_preserves_dated_amd_case_layout_and_source_holds[desktop]`
  failed to launch system Chrome in this sandbox. That is not a whole-suite pass.
- One existing mocked server-log regression initially failed at `_free_port()`
  because it unnecessarily acquired a real socket. Mocking that acquisition,
  consistent with its already mocked process/health check, preserves both log
  assertions and removes the unrelated environmental requirement. Actual browser
  tests retain real server startup.
- Independent review found and reproduced three material issues: incomplete
  supporting evidence, ambient pytest options and mismatched browser selection.
  Each was addressed with regressions observed failing then passing. The Python
  minimum was clarified. No second independent review is claimed.
- Protected inputs and data/output/asset manifests remain unchanged. Source
  rights, actual records, canonical rows, credentials and hosting were not changed.

## Remaining evidence

The actual exact-head browser and whole-suite results belong to CI. Independent
researcher completion, target-persona fit, operated access/recovery and data
permissions remain separate. No testers were contacted and no user sessions or
live source results were fabricated. The implementation reused the existing
isolated checkout under the user's instruction to execute the goal; the original
checkout remains untouched.

[Executable goal prompt](goals/VERIFIED_RESEARCH_JOURNEY_GOAL.md) ·
[Self-service method](SELF_SERVICE_COMPANY_RESEARCH.md) ·
[Private-pilot boundaries](PILOT_READINESS_AUDIT.md)
