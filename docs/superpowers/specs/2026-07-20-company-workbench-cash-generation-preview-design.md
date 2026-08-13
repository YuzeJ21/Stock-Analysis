# Company Workbench Cash-Generation Activation Preview Design

## Goal

Add an explicit, read-only Company Workbench preview that demonstrates how one accepted SEC quarterly cash-generation evidence packet would appear in the research workflow without activating production evidence, persisting data, rebuilding readiness, or changing any independent readiness state.

The preview is product evidence for a controlled local beta. It is not a recommendation, forecast, production-data activation, broad-coverage claim, or market-validation result.

## Scope

The slice covers one explicit preview route:

`?mode=research&page=company-workbench&ticker=NVDA&open=1&cash_preview=1`

The route may display quarterly operating margin, free cash flow, and FCF margin only when a supplied `SecQuarterlyPilotPreview` has status `accepted_for_review` and passes the activation-preview contract. The ordinary Company Workbench route remains unchanged and continues to load canonical quarterly actuals without supplemental SEC preview observations.

The slice does not add production activation, canonical persistence, readiness promotion or rebuild, broad SEC collection, another-company proof, hosted deployment, consensus data, calibrated probabilities, or generated CSV, JSON, report, screenshot, timing, or readiness artifacts.

## Architecture

Create a focused pure module for the activation-preview boundary. It accepts a `SecQuarterlyPilotPreview` plus the explicit review cutoff and returns one immutable preview view model. The module does not fetch, read, or write files and does not import the Streamlit dashboard.

The view model contains:

- ticker, fiscal period, preview status, and a stable human message;
- independently composed operating-margin, free-cash-flow, and FCF-margin preview metrics;
- visible blocker and withheld-metric tuples;
- exact SEC accession, source URL, acceptance time, cutoff, source references, and capex-sign evidence;
- immutable `production_activation=False` and `readiness_promotions=()` fields;
- an explicit `persistence=False` boundary.

The existing `SecQuarterlyPilotPreview` remains the source-review result. The new contract is a downstream presentation review only; it does not mutate or reinterpret adapter acceptance.

## Data Flow

1. An explicit preview caller obtains one in-memory `SecQuarterlyPilotPreview` through the existing bounded SEC extraction and acceptance path.
2. The activation-preview composer rejects any result whose status is not `accepted_for_review`, whose acceptance object is absent or not accepted, whose ticker does not match the selected Workbench ticker, whose cutoff is absent or invalid, or whose non-activation invariants are not intact.
3. For accepted input, the composer calls the existing quarterly trend composition with the SEC extraction's Revenue actual and cash-generation observations.
4. The composer exposes only the three cash-generation metric results in its primary answer. Revenue and EPS readiness remain owned by the existing canonical Company Workbench packet and are not promoted by the preview.
5. The explicit Workbench preview route renders the preview panel before technical evidence and leaves the normal `quarterly_trend_packet` unchanged.
6. Exact component lineage, cutoff, acceptance time, accession, capex-sign proof, definitions, and diagnostics render under a collapsed Advanced preview-evidence disclosure.

No preview result enters `data/`, `outputs/`, canonical ledgers, session proof ledgers, saved readiness, valuation inputs, Earnings Nowcast, Monitor, or downstream forecasts.

## Explicit Preview Route

`cash_preview=1` is the only accepted activation-preview query value. Missing, empty, or any other value keeps the ordinary Company Workbench behavior.

The preview route is local and opt-in. It must not be added to the default Research Desk, Discover, Company Workbench, or Monitor navigation. It must not silently fetch data during normal Workbench rendering.

The explicit route uses a dedicated preview loader with the already bounded NVIDIA filing identity and the reviewed cutoff `2026-07-20T23:59:59-04:00`. The route does not accept an arbitrary company, accession, filing, or cutoff from query parameters. This makes the first user-flow proof reproducible and prevents the preview flag from becoming a broad collection surface. If the required SEC user agent, network access, exact filing payload, or evidence contract is unavailable, the route returns a visible withheld preview. It does not fall back to fixtures, canonical rows, alternate providers, inferred values, or stale cached payloads.

## User Experience

The primary panel appears inside Business Trend and is labelled:

`Cash-generation review preview — not production evidence`

The panel answers three questions:

- What operating margin does the accepted packet support for the filed quarter?
- What free cash flow does the accepted packet support using explicit signed capital expenditures?
- What FCF margin follows from compatible Revenue and free-cash-flow evidence?

Each metric keeps its own state. If the complete packet cannot support all required preview metrics, the panel displays all three as withheld rather than leaking partial numeric output.

The panel always displays the boundaries `production activation: false`, `readiness promotions: none`, and `no persistence or readiness rebuild`. Technical component values, inline-XBRL identifiers, definitions, source references, accession, timestamps, and diagnostics stay under Advanced.

The ordinary Business Trend cards continue to show canonical Revenue and EPS and continue to withhold operating margin, free cash flow, and FCF margin unless separately activated in a future approved slice.

## Fail-Closed Rules

The preview is fully withheld when any of these conditions holds:

- preview or adapter status is not `accepted_for_review`;
- production activation is true or readiness promotions are non-empty;
- the selected ticker and extraction ticker differ;
- the cutoff is missing, malformed, or earlier than the filing acceptance time;
- the SEC extraction contains blockers;
- accession, source URL, acceptance time, or capex-sign evidence is missing;
- capex sign is not `explicit_filed_table_outflow`;
- observations are empty, mixed-ticker, mixed-source, post-cutoff, ambiguous, incomplete, or definition-incompatible;
- required operating-margin, free-cash-flow, or FCF-margin output is absent;
- Q4 evidence lacks an explicit filed three-month quarter.

Blocked results retain stable blocker codes and expose no partial numerical preview. Synthetic fixtures remain test-only.

## Readiness Independence

The preview cannot change or imply readiness for actuals, consensus, Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, catalysts, outcomes, peers, backtesting, or calibration.

Revenue is used only as an explicit compatible component for the preview calculation. It is not copied into canonical actuals or used to alter the ordinary Company Workbench Revenue state. EPS remains unverified unless explicit split-basis proof exists. No numerical Beat/Miss probability is introduced.

## Testing

Behavior changes are test-driven. The focused tests must prove:

- an accepted in-memory SEC result composes all three preview metrics;
- the immutable non-activation, no-persistence, and empty-readiness-promotion fields;
- exact accession, source, acceptance time, cutoff, source references, and capex-sign lineage;
- full withholding for rejected, blocked, absent-acceptance, mismatched-ticker, post-cutoff, incomplete, ambiguous, incompatible, and invalid-capex-sign inputs;
- no partial numeric leakage when one required metric fails;
- the explicit `cash_preview=1` query contract;
- answer-first rendering and collapsed Advanced evidence;
- the normal Company Workbench route continues to use the unchanged canonical packet and does not fetch or activate SEC preview evidence;
- no preview output or Make target accepts an output path, apply flag, readiness flag, broad-refresh flag, or fixture fallback.

After focused tests, run the complete repository test suite and all required dashboard, render, public, commercial-beta, release, pilot-readiness, diff-hygiene, PR-range-hygiene, whitespace, and staged-hygiene gates.

## Documentation and Release Evidence

After the implementation passes, update `ROADMAP.md`, `docs/PERSONAL_RESEARCH_MODE.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE.md`, the continuation goal prompt, and draft PR #113. Documentation must state that the preview proves one explicit user-flow composition only and does not prove production activation, a second company, historical depth, Q4 coverage, hosting, external reviewer adoption, demand, calibration, or product-market fit.

Stage only the exact product, test, documentation, specification, and plan files. Keep all generated artifacts excluded. Push only `codex/personal-research-mode-mvp` and keep PR #113 draft.

## Next Maturity Decision

Once this slice is verified, assess a second-company bounded SEC portability proof against remaining local alternatives. A second-company proof is justified only if it adds evidence about parser and adapter portability that the Workbench preview cannot provide. It remains a separate approved slice and must use one exact filed quarter, official SEC endpoints, in-memory processing, explicit Q4 avoidance or evidence, and no generated artifacts or production activation.
