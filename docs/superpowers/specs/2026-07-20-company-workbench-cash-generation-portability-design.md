# Company Workbench Cash-Generation Portability Design

## Purpose

The current Company Workbench cash-generation preview proves one exact NVIDIA filing and one explicit preview-only user flow. A no-write eligibility review of AMD Q1 FY2026 now provides a second exact official SEC filing that passes the existing extraction, source-rights, adapter-acceptance, cutoff, and capex-sign contracts. The next slice should turn that evidence into a bounded two-company portability proof without broadening coverage, accepting caller-supplied filing identity, persisting data, or changing production readiness.

This is research-only product evidence. It is not investment advice, a recommendation, a production source activation, broad commercial coverage, or market validation.

## Verified Eligibility Evidence

The second-company eligibility review used the existing read-only SEC preview command with one exact identity:

- ticker: `AMD`
- CIK: `0000002488`
- fiscal period: `2026-Q1`
- period start: `2025-12-28`
- period end: `2026-03-28`
- accession: `0000002488-26-000076`
- primary document: `amd-20260328.htm`
- SEC acceptance time: `2026-05-05T22:06:27+00:00`
- fixed review cutoff: `2026-07-20T23:59:59-04:00`

The existing contract accepted Revenue USD 10.253B, operating income USD 1.476B, cash from operations USD 2.955B, and capital expenditures USD -0.389B. Capital expenditures became a negative cash outflow only after the exact filed table supplied `explicit_filed_table_outflow` evidence. Derived free cash flow is USD 2.566B. The command fetched only Companyfacts, submissions, and the exact primary filing in memory and produced no file or readiness change.

This evidence proves eligibility for one bounded implementation slice. It does not prove historical depth, Q4 support, a third company, broad parser portability, provider redundancy, external reviewer adoption, demand, calibration, or product-market fit.

## Approaches Considered

### 1. Immutable filing registry — selected

Store the two reviewed filing identities in immutable application configuration and let the loader select only by normalized ticker. This removes duplicated NVIDIA-only constants while ensuring URL parameters cannot choose a CIK, accession, dates, document, or cutoff. It is the smallest change that proves the same loader and composition path works for two exact companies.

### 2. Separate AMD loader

Add a second loader that copies the NVIDIA sequence with AMD constants. This minimizes edits to the existing loader but duplicates fetch, extraction, rights, exception, and composition logic. The duplicate paths could drift and would not provide as strong a portability result.

### 3. Caller-supplied filing parameters

Allow query parameters or loader arguments to provide CIK, accession, dates, filing, and cutoff. This would be flexible but would weaken the reviewed-identity boundary and create an implicit broad-source surface. It is rejected.

## Architecture

### Immutable filing specification

Add a frozen `CashGenerationPreviewFiling` value type to `src/company_workbench_cash_generation_preview_loader.py`. It contains:

- `ticker`
- `cik`
- `fiscal_period`
- `period_start`
- `period_end`
- `accession`
- `primary_document`
- `as_of`

Expose a read-only mapping with exactly two entries: the already reviewed NVIDIA Q1 FY2027 filing and the eligible AMD Q1 FY2026 filing. The registry is application configuration, not canonical research data. It must not be loaded from CSV, JSON, environment variables, URL parameters, or a generated artifact.

### Bounded loader dispatch

`load_company_workbench_cash_generation_preview(ticker, *, user_agent=None, fetcher=None, retrieved_at=None)` keeps its public signature. It normalizes the ticker, looks it up in the immutable registry, and returns a complete withheld preview before fetching when no exact entry exists.

For an exact entry, the loader:

1. fetches only the three existing official SEC endpoints using that entry's CIK, accession, and primary document;
2. calls the existing extractor with the entry's exact fiscal identity, dates, filing identity, retrieval time, and cutoff;
3. evaluates the existing immutable source-rights and adapter-acceptance contracts;
4. composes the existing Company Workbench preview using the same cutoff and selected ticker;
5. converts supported fetch, identity, and parsing exceptions into a stable all-or-nothing withheld result without exposing exception text.

An unsupported ticker must not fetch and must not leak another company's fiscal period, accession, source URL, components, or values.

### Explicit Workbench routes

The existing query gate remains exact: only `cash_preview=1` invokes the loader. The two explicit routes are:

- NVIDIA: `?mode=research&page=company-workbench&ticker=NVDA&open=1&cash_preview=1`
- AMD: `?mode=research&page=company-workbench&ticker=AMD&open=1&cash_preview=1`

No default navigation link includes `cash_preview=1`. The normal Company Workbench route never loads the preview and continues to render canonical evidence and existing production withheld states.

The presentation layer remains company-agnostic. Accepted AMD evidence uses the same three preview-only primary cards and collapsed Advanced lineage. The cards never use `ready`. Accession, URL, timestamps, exact components, definitions, source references, capex-sign state, cutoff, and blockers remain Advanced-only.

## Data and Trust Boundaries

Both companies retain the same invariants:

- `production_activation=false`
- `readiness_promotions=()`
- `persistence=false`
- no canonical source row
- no readiness rebuild or promotion
- no forecast, valuation, consensus, peer, catalyst, outcome, backtest, or calibration change
- no cache, CSV, JSON, report, sample report, screenshot, timing output, or generated artifact
- no Q4 derivation
- no inference of source identity, period identity, accounting compatibility, publication time, or capex sign

Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, catalysts, outcomes, consensus, backtesting, and calibration keep independent readiness states. A successful AMD preview cannot borrow or promote any sibling state.

## Failure Behavior

The preview is all-or-nothing. Any missing or conflicting Companyfacts value, CIK mismatch, accession mismatch, primary-document mismatch, missing or invalid acceptance time, post-cutoff evidence, missing exact inline fact, missing explicit capex outflow presentation, rights failure, unsupported field, adapter blocker, ticker mismatch, incompatible component, incomplete derived set, forbidden activation, or forbidden readiness promotion withholds all three preview metrics and all components.

The primary answer must not show partial values. Stable blocker identifiers and exact technical lineage remain available only under Advanced when the result contract permits them. Fetch or parsing exceptions are represented by exception type only; secret-bearing or provider error text is never rendered.

Removing the AMD registry entry is the rollback. After removal, the explicit AMD route returns an unsupported-ticker withheld result before any fetch. No data rollback is required because the feature never persists data.

## Testing Strategy

### Loader contract

Extend `tests/test_company_workbench_cash_generation_preview_loader.py` to prove:

- both immutable entries have the exact reviewed identity;
- NVIDIA still fetches exactly its three endpoints and produces its existing result;
- AMD fetches exactly its three endpoints and produces the reviewed Q1 FY2026 result;
- AMD free cash flow is USD 2.566B and all three derived metrics are `preview_available`;
- unsupported tickers fetch nothing and leak no configured filing identity;
- malformed or unsigned AMD evidence withholds every value and component;
- the loader signature still exposes no caller-supplied CIK, accession, filing, cutoff, output, apply, refresh, or readiness parameter;
- the module exposes no file writer, broad provider, fallback, or generated-artifact surface.

### Dashboard and presentation contracts

Extend the existing dashboard contract and render-smoke tests to prove:

- the explicit AMD route invokes the bounded loader and renders accepted preview cards without live network access in the test;
- the normal AMD route never invokes the loader;
- AMD technical lineage remains below the primary cards and inside Advanced;
- default navigation still contains no preview flag;
- preview states never become production `ready` states.

### Regression and release verification

Run the focused cash-generation, loader, workspace, dashboard-contract, render-smoke, and documentation suites first. Then run the complete repository test and release-gate sequence required by the continuation contract. Verify exact staged paths and PR-range hygiene before commit and push. Wait for GitHub CI on the exact pushed head.

## Documentation and Product Claims

Update `ROADMAP.md`, `docs/PERSONAL_RESEARCH_MODE.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`, the continuation goal prompt, and draft PR #113 after implementation passes.

The documentation may claim:

- two exact official SEC filings pass one shared bounded parser, loader, acceptance, and Workbench preview path;
- the implementation is a stronger portability and reliability proof than the NVIDIA-only path;
- both routes preserve exact lineage, complete withholding, no persistence, and no activation.

The documentation must not claim:

- broad company coverage;
- arbitrary-filing support;
- production source activation;
- current readiness;
- historical or Q4 coverage;
- point-in-time consensus availability;
- calibrated probability;
- hosted reliability or access control;
- external reviewer validation;
- commercial demand or product-market fit.

## Completion Criteria

This slice is complete only when:

1. the immutable registry contains exactly the reviewed NVIDIA and AMD entries;
2. both explicit routes use the same bounded loader and preview composition;
3. unsupported tickers fail before fetch without another company's metadata;
4. the AMD fixture and exact live filing evidence both pass the same required component and capex-sign contract;
5. all failure paths retain complete withholding and no component leakage;
6. normal Company Workbench navigation and canonical evidence remain unchanged;
7. all focused and full local gates pass;
8. generated-artifact and PR-range hygiene remain clean;
9. documentation and PR #113 state the narrow two-company boundary accurately;
10. the branch is pushed only to `codex/personal-research-mode-mvp`, PR #113 remains draft, and exact-head GitHub CI succeeds.

Passing these criteria closes one bounded two-company portability slice only. The overall commercial-maturity goal remains active because source, hosted-preview, reviewer, calibration, evidence-depth, and operating gates remain incomplete.
