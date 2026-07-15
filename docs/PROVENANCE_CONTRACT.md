# Provenance Contract

This contract defines the minimum evidence boundary for Stock Research Command Center. It applies to the dashboard, reports, imported rows, and public demo package.

The product principle remains: data readiness first, analysis second, research decision last. A displayed calculation is not an investment recommendation, and an unavailable input remains unavailable.

## Record Contract

Every analysis-ready record or report section should expose, directly or through its source/readiness detail:

| Field | Meaning | Boundary |
| --- | --- | --- |
| `readiness_state` | `ready`, `partial`, `blocked`, `excluded`, or an evidence outcome such as `candidate_context_only`. | A state is not a recommendation. |
| `source` | Named local, SEC, provider, filing, or reviewed source origin. | Source availability alone does not render a value usable. |
| `as_of_date` | Financial period, market date, filing date, or source effective date. | It is not the same as retrieval time. |
| `reporting_period` | Fiscal period attached to a financial, earnings, or estimate record, where supplied. | A reporting period is not inferred from the retrieval date or a market price date. |
| `currency` | Source-supplied price or financial currency, where available. | The product does not infer currency, perform cross-currency conversion, or treat absent currency as a common unit. |
| `retrieved_at` | When a provider or local artifact was obtained, where available. | Missing retrieval time lowers freshness certainty; it does not get invented. |
| `method_version` | Version of the project rule or calculation that produced the section. | Method changes must be documented before public claims change. |
| `missing_inputs` | Required fields that are absent, stale, malformed, or unproven. | Missing inputs suppress the dependent conclusion. |
| `confidence_boundary` | Plain-language limit on how the section can be used. | It must never override a blocked or excluded state. |

## Lane Requirements

| Lane | Minimum source evidence | What stays withheld without it |
| --- | --- | --- |
| Price and risk context | Valid OHLCV rows with date and provider/source context. | Trend, momentum, and risk claims beyond the available history. |
| Fundamentals | Source-backed financial fields plus reporting period/as-of information. | Quality, leverage, margin, or growth interpretation for absent fields. |
| Share count | Explicit filing or trusted source fact with date/context. | Per-share DCF math; shares are never inferred from price or market cap. |
| DCF | Price, revenue, free cash flow or FCF margin, shares, method assumptions, and company eligibility. | Fair-value scenario math and valuation interpretation. |
| Candidate peers | Industry, SIC, product, or other contextual suggestion. | Candidate context must not satisfy trusted-peer readiness. |
| Trusted peers | Source-backed relationship, review rationale, source/as-of date, and required peer inputs. | Peer-relative valuation and comparative conclusions. |
| Earnings and estimates | Trusted provider/import fields, fiscal period, source, and retrieval/as-of context. | Optional readiness or consensus interpretation from date-only or target-only rows. |
| Earnings Nowcast | Prior quarterly actuals plus an exact-period point-in-time consensus snapshot, all timestamped no later than the forecast cutoff; model version and input hash are mandatory. | Revenue/EPS range, consensus-relative classification, and every probability output. Candidate signals never satisfy this gate. |

## Earnings Nowcast Point-In-Time Contract

Every forecast event must preserve `ticker`, `fiscal_period`, `as_of_timestamp`, expected report date and forecast horizon when known, source publication/retrieval timestamps, direct source references, Revenue/EPS metric definitions, `model_version`, `input_snapshot_hash`, readiness/freshness states, and source IDs. Historical consensus snapshots are append-only evidence. An exact duplicate is not re-added; a revised or currently visible estimate is retained as a separate revision and must not overwrite the snapshot that was knowable at a prior cutoff. Duplicate actual rows cannot inflate quarterly history, and conflicting actuals remain blocked unless an explicit `supersedes_source_ref` resolves the revision chain.

The target-period actual and every source published after the cutoff are evaluation evidence only and must never enter forecast inputs. Trusted peer/news signals require explicit source, publication time, excerpt hash, review state, and trusted-peer relationship evidence where applicable. They remain directional context and cannot create a numeric adjustment or numerical probability.

The synthetic fixture packet is software-test evidence only. Real output remains `awaiting_point_in_time_consensus`, and numerical probability remains `awaiting_calibration_evidence` until the documented out-of-sample gates pass.

## Freshness Rules

Freshness is lane-specific. A price date, a filing date, and a peer review date answer different questions.

- Price context: use the latest available market date and row-history depth; a short history may remain partial.
- Fundamentals and share count: use filing date and reporting period; quarterly or annual changes do not invalidate an older filing, but the report should surface its period.
- Peer mappings: use source review date; candidate suggestions do not acquire freshness merely because price data refreshed.
- Earnings and estimates: use provider retrieval and estimate period; unsupported fields remain optional context only.
- Earnings Nowcast: use the forecast cutoff, actual publication time, consensus snapshot time, retrieval time, and fiscal-period identity. A current price or later revised estimate cannot refresh an older point-in-time forecast.
- Screenshots and the demo manifest show product/package evidence. They are not data-freshness proof.

## Method Versioning

The current public methodology is **v1 readiness-first deterministic gates**. A change to a gate, valuation formula, eligibility rule, assumption cap, source normalization, or public interpretation must:

1. Update `docs/METHODOLOGY.md` and this contract.
2. Add or update regression tests for the changed rule.
3. Preserve prior readiness truth until source rows are rebuilt and reviewed.
4. Surface the new `method_version` in the affected report or data artifact when that output is regenerated.

## Demo Boundary

The `demo` profile is a compact tracked snapshot with a manifest, checksums, selected tickers, and known limitations. It proves that the product workflow can render and explain readiness states. It is not data-freshness proof and does not unlock blocked inputs.

The `local` profile is an ignored mutable workspace for refreshed research data. It may contain newer local rows, but those rows need the same validate, preview, apply, rebuild, and proof gates before they change a readiness claim.

Both profiles remain research-only: no broker execution, order routing, auto-trading, direct buy/sell instructions, or fabricated values.
