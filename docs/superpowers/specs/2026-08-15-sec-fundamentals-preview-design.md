# SEC Fundamentals No-Write Preview Design

**Status:** Approved for bounded local implementation. Canonical apply, source-rights expansion, release recording, and remote synchronization are not authorized.

## Purpose

Provide a deterministic, inspection-only comparison between the current canonical fundamentals row and a fresh official SEC Companyfacts candidate for at most five explicitly named tickers. The first cohort is AAPL, AMZN, and GOOG.

The preview exists to expose stale, mixed-period, missing, unsupported, and derived evidence. It does not promote readiness or decide that a candidate may be published.

## Request and No-Write Boundary

- Accept only explicit tickers and reject an empty list or more than five unique tickers.
- Fetch only the SEC ticker map and SEC Companyfacts HTTPS endpoints with an identifying `SEC_USER_AGENT`.
- Do not call any fallback provider, scraper, search result, or paid API.
- Add a true no-cache adapter path: when cache is disabled, neither ticker-map nor Companyfacts path resolution may create directories or files.
- Read canonical `data/fundamentals.csv` and, when present, the ignored staged fundamentals header only for comparison. Never normalize, rewrite, delete, or apply either file.
- Print deterministic JSON to stdout. Tests may use an isolated `/tmp` fixture, but production code has no output-file option.

## Candidate and Provenance Model

The existing SEC extractor remains the source of candidate calculations. It will also expose private field-provenance metadata that the staging writer omits. Each field reports:

- canonical and SEC candidate values;
- `changed`, `unchanged`, or `missing` value status;
- fiscal period start/end when applicable;
- filing date, accession, form, taxonomy, concept, unit, and exact SEC Companyfacts URL;
- `direct` or `derived` value kind;
- one fail-closed classification and its publishability blocker.

The preview covers the SEC-backed canonical fields currently produced by the extractor: revenue, revenue growth, EPS, free cash flow, FCF margin, profit margin, operating margin, EBITDA, cash, debt, and shares outstanding. Source components such as operating income, cash from operations, and capital expenditures remain provenance inputs, not silently added canonical columns.

## Coherence Rules

Revenue's latest annual record defines the candidate fiscal-period anchor. Annual flow facts must use that period. Instant facts must be tied to the same filing accession or exact period end. Derived fields inherit every component's context. Revenue growth may intentionally use the anchored annual period and its immediately prior annual period.

When a component cannot be tied to that context, the observed value may be shown for diagnosis but is classified `period_conflict` or `source_context_ambiguous` and is blocked from publication. Missing facts remain unavailable; they never become zero.

## Source-Rights Classification

Classifications are resolved in this order:

1. `missing` when no candidate fact exists.
2. `period_conflict` when a period-specific fact conflicts with the annual anchor.
3. `source_context_ambiguous` when filing/accession context cannot be tied to the anchor.
4. `derived_scope_review_required` for every calculated field, even when its source components are registered.
5. `approved_direct` only when the exact direct field is listed for `sec_companyfacts` in `config/source_rights.yml`.
6. `unsupported` for a present direct field outside the registered field scope.

No preview result changes the source-rights registry. Filing metadata is evidence context, not permission to publish an otherwise unsupported field.

## Schema Risk

The result reports:

- candidate provenance components that are not canonical columns;
- canonical columns not produced by this SEC candidate;
- columns found in the ignored staged fundamentals file but absent from canonical fundamentals;
- columns that a naïve full-row rewrite would drop or add.

The preview never adds `currency` or any other column and never rewrites the full dataset for one ticker.

## Failure States

- Missing `SEC_USER_AGENT`, invalid ticker input, a non-SEC request, malformed payload, unresolved CIK, or missing canonical row is reported explicitly and fails closed.
- One ticker's failure does not fabricate values for that ticker or change another ticker's result.
- Analyst estimates, targets, ratings, recommendations, prices, peer decisions, and quarterly cash-flow derivations are outside this command.

## Verification

Tests must prove the ticker cap, official-endpoint restriction, true no-cache behavior, deterministic deltas, direct-versus-derived classification, missing and malformed fail-closed behavior, mixed-period blocking, staged schema reporting, AAPL mixed-period visibility, and GOOG explicit-share unavailability. Before and after hashes must prove that tracked `data/` and `outputs/` plus the existing ignored cache/staging files remain byte-identical.
