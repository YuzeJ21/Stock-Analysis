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
- `confidence`
- `main_reason`
- `supporting_features`
- `blocked_features`
- `excluded_features`
- `missing_data`
- `next_action`
- `data_readiness_score`
- `analysis_score`
- `decision_score`
- `updated_at`

## Decision Rules

- A ticker must not be classified as `Research Now` when required data is insufficient.
- A ticker with missing price data is normally `Blocked by Data`.
- A ticker with only metadata and no analysis-ready features is `Review Later` or `Blocked by Data`.
- ETF/index proxy rows should be excluded from DCF, but may be monitored for market direction, momentum, risk, or correlation if price data supports it.
- Missing fundamentals block DCF and prevent undervaluation/overvaluation conclusions.
- Missing earnings and analyst estimates should not reduce core momentum readiness, but they must be listed as blocked optional features.
- Confidence must be reduced when important data is missing.

## Examples

`META`

- `decision_bucket`: `Blocked by Data`
- `main_reason`: `Missing usable price data`
- `next_action`: `Import staged price rows or refresh price provider`

`QQQ`

- `decision_bucket`: `Monitor` when price-ready
- `main_reason`: `ETF usable for market context and risk; excluded from DCF`
- `excluded_features`: `dcf`

`NVDA`

- May be `Monitor` or `Research Now` only if readiness supports it.
- If DCF/fundamentals are partial, confidence must reflect the missing fields.
