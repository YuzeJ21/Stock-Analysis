# Trusted-Data Profile Resolution Design

## Problem

The trusted-data pilot CLI describes current local blockers but directly reads `data/` and `outputs/`. Setting `STOCK_RESEARCH_DATA_PROFILE=local` therefore still ranks the tracked default readiness package. This can return work that is already complete in the ignored local research profile. MU is the concrete regression: default readiness reports `peer_ready=False`, while `data/local/reports/ticker_readiness_report.csv` reports `peer_ready=True`.

The mismatch affects candidate ranking, one-ticker packets, evidence boards, before/after comparisons, import/rejection status, reviewed-proof filtering, SEC cache reads, and generated stock-report mode lookup.

## Approved Approach

Reuse the existing profile resolver in `src.paths` for every trusted-data read:

- `resolve_data_dir(project_root=root)` for canonical data, imports, cache, reports, rejected rows, and proof history.
- `resolve_outputs_dir(project_root=root)` for worklists, preflight output, and stock reports.
- `format_path_context(project_root=root)` at the CLI boundary so every command names the selected paths.

No new profile configuration, command variant, or data schema is introduced. With no environment override, behavior remains the current `default` profile. `demo` and `local` use their existing isolated directories.

## Behavioral Contract

1. Every trusted-data pilot read in one process uses the profile selected by `STOCK_RESEARCH_DATA_PROFILE`.
2. Candidate ranking, packet rendering, board rendering, lane rendering, and evidence generation cannot mix default and selected-profile files.
3. CLI output prints project, data, and outputs paths before the trusted-data result.
4. The workflow remains read-only unless the existing explicit evidence-write command is requested.
5. Readiness definitions, candidate priorities, source gates, and research-only wording do not change.
6. Missing selected-profile files fail closed as missing evidence; the command must not silently fall back to default-profile files.

## Verification

- Add a regression fixture where default MU is peer-blocked and local MU is peer-ready.
- Prove default selection still returns MU and local selection excludes MU.
- Prove packet/report/local-file status reads only selected-profile files.
- Prove CLI output names selected paths.
- Run focused trusted-data/path tests, the full test suite, public checks, hygiene checks, and a live local-profile command.

## Non-Goals

- No provider refresh, import apply, readiness rebuild, or coverage change.
- No generated CSV/report staging.
- No changes to peer trust policy or candidate-to-trusted promotion.
- No fallback from a missing selected profile to default data.
