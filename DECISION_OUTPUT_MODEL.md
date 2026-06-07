# Decision Output Model

## Decision Buckets

`Research Now`

The ticker has enough data for at least the intended research workflow and has supportive analysis evidence.

`Monitor`

The ticker has enough data for useful monitoring, but the current setup does not warrant immediate deeper research.

`Blocked by Data`

Required data is missing. The ticker must not be treated as a weak recommendation.

`Excluded`

The ticker or asset type does not apply to the requested analysis, such as ETF/index proxy exclusion from DCF.

`Review Later`

The ticker is known but not urgent, not sufficiently supported, or outside the active research priority.

## Required Columns

Each ticker-level decision row should include:

- `ticker`
- `name`
- `asset_type`
- `exchange`
- `sector`
- `industry`
- `theme`
- `decision_bucket`
- `decision_subtype`
- `confidence`
- `main_reason`
- `primary_blocker`
- `supporting_features`
- `blocked_features`
- `excluded_features`
- `missing_data`
- `next_action`
- `next_best_action`
- `data_readiness_score`
- `readiness_score`
- `data_confidence`
- `evaluation_status`
- `purpose_fit`
- `setup_quality`
- `valuation_view`
- `risk_view`
- `missing_data_summary`
- `next_research_step`
- `source_freshness_summary`
- `analysis_score`
- `decision_score`
- `updated_at`

## Evaluation Brief Columns

The command center may add interpretation fields that summarize the decision row for
dashboard and stock-report use. These fields must remain research-only and must not
turn missing data into recommendations.

- `purpose_thesis`: the current purpose read for the ticker.
- `purpose_alignment`: whether available local evidence still matches that purpose.
- `setup_evaluation`: what setup state is supported by current price/momentum outputs.
- `valuation_evaluation`: valuation interpretation, including DCF exclusion or peer limits.
- `supported_analysis`: analysis areas currently supported by trusted local data.
- `unsupported_analysis`: analysis areas intentionally withheld because inputs are missing or excluded.
- `risk_watchpoint`: the main analysis risk or limitation to monitor.
- `invalidation_condition`: a research invalidation condition, not a transaction instruction.
- `next_research_question`: the next manual research question or data-unlock question.
- `review_priority_reason`: why the row deserves review, monitoring, or data unlock next.
- `confidence_explanation`: why confidence is high, medium, low, or blocked.
- `feature_summary`: compact ready/partial/blocked/excluded feature summary.

## Current Review Details

The product uses the internal `decision_subtype` field to show a plain review
detail for each broad bucket without turning it into a recommendation.

- `Research Candidate - Core Data Ready`: core company data is ready for a supported research pass.
- `Research Candidate - DCF Ready But Peer Blocked`: standalone DCF is ready, but peer-relative valuation waits for source-backed peer inputs.
- `Research Candidate - Optional Context Locked`: core research may be supported, but earnings or analyst-estimate context remains unavailable.
- `Monitor - ETF Market Proxy`: ETF/index/fund rows can support market, theme, liquidity, or risk monitoring while operating-company DCF is excluded.
- `Monitor - Price/Momentum Ready`: price/setup context is useful, but deeper company research remains partial.
- `Blocked by Data - Missing Price`: usable price history is missing.
- `Blocked by Data - Missing Fundamentals`: fundamentals or DCF inputs are missing.
- `Blocked by Data - Missing Peer Mapping`: source-backed peer mapping or peer input context is the main blocker.
- `Excluded - DCF Not Applicable`: the requested valuation method does not fit the asset type.

Subtypes are review-queue labels, not action instructions.

## Confidence And Scores

Decision scores are data-quality and triage aids.

- `data_readiness_score` / `readiness_score`: normalized support from ready, partial, blocked, and excluded feature states.
- `analysis_score`: normalized review context from existing analysis outputs when available.
- `decision_score`: confidence expressed on a 0-100 scale for sorting/review only.
- `data_confidence`: plain label such as `high`, `medium`, `low`, or `blocked`.
- `confidence_explanation`: the human-readable reason confidence is reduced or supported.

Scores must not be displayed as price targets, expected returns, or direct
portfolio actions. Missing fundamentals, DCF, peers, earnings, or estimates
should reduce confidence or keep analysis blocked.

If a report or dashboard displays `Base score`, `WatchlistScore`,
`decision_score`, or `CompositeScore`, it must explain that the number is a
review-order or confidence aid only.

## Decision Rules

- A ticker must not be classified as `Research Now` when required data is insufficient.
- A ticker with missing price data is normally `Blocked by Data`.
- A ticker with only metadata and no analysis-ready features is `Review Later` or `Blocked by Data`.
- ETF/index proxy rows should be excluded from DCF, but may be monitored for market direction, momentum, risk, or correlation if price data supports it.
- Missing fundamentals block DCF and prevent undervaluation/overvaluation conclusions.
- Missing earnings and analyst estimates should not reduce core momentum readiness, but they must be listed as blocked optional features.
- Confidence must be reduced when important data is missing.
- `primary_blocker`, `missing_data_summary`, `next_action`, and `next_best_action` must identify the next trusted local data-unlock step when a row is blocked.
- `evaluation_status`, `purpose_fit`, `setup_quality`, `valuation_view`, and `risk_view` must explain the current state in research-only language.
- ETF/index/fund rows must show DCF as excluded when operating-company valuation does not apply.

## Examples

`META`

- `decision_bucket`: `Blocked by Data`
- `main_reason`: `Missing usable price data`
- `next_action`: `Import price rows through the preview-first workflow or refresh the price provider`

`QQQ`

- `decision_bucket`: `Monitor` when price-ready
- `main_reason`: `ETF usable for market context and risk; excluded from DCF`
- `excluded_features`: `dcf`

`NVDA`

- May be `Monitor` or `Research Now` only if readiness supports it.
- If DCF/fundamentals are partial, confidence must reflect the missing fields.
