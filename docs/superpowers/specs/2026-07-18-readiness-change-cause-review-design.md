# Readiness Change Cause Review Design

## Purpose

The no-write readiness preview reports 652 changed tickers. The promotion-evidence review explains 152 fundamentals promotions and 146 overlapping DCF promotions, but most remaining movement is still presented only as changed field names. Reviewers cannot readily distinguish a deliberate method exclusion from a partial-input transition or a new universe row.

Add a semantic, reason-coded change-cause review to the same stdout-only command. It must explain the movement without altering readiness, source inputs, exclusion rules, or generated artifacts.

## Approaches Considered

1. **Semantic transition review with named exclusion reasons (selected).** Expose stable reason codes from the existing company-scope method and summarize newly ready, partial, excluded, added, and removed transitions independently.
2. **Raw field-signature counts.** Easier, but labels such as `blocked_features -> excluded_features` still require implementation knowledge.
3. **Documentation-only explanation.** Non-repeatable and likely to become stale when the universe or method changes.

## Company DCF Exclusion Reasons

Refactor the current ordered regular expressions into named, behavior-equivalent reasons:

- `non_operating_asset_type`;
- `acquisition_or_spac`;
- `closed_end_fund`;
- `bank_or_bancorp`;
- `financial_insurance_or_mortgage`;
- `reit`;
- `realty_trust_or_bdc`;
- `capital_corporation`;
- `nonpositive_revenue_margin_model`.

`company_dcf_exclusion_reasons(...)` returns every matching reason in deterministic order. Existing boolean helpers delegate to it so the current exclusion decision does not change. The preview uses the first reason as the primary mutually exclusive summary reason and reports any unexplained exclusion separately.

## Change Review

For saved versus proposed frames, summarize independently:

- added and removed ticker rows;
- newly ready feature counts;
- newly partial feature counts;
- newly excluded feature counts;
- primary reasons for newly excluded DCF rows;
- unexplained newly excluded DCF rows.

Counts are transition counts, not current readiness counts and not mutually exclusive ticker cohorts. The output says so explicitly. Promotion evidence remains a separate section because technical movement, provenance, commercial rights, and field scope answer different questions.

## Failure Behavior

- Missing metadata or fundamentals remains an explicit `unexplained` DCF exclusion; no reason is inferred.
- Duplicate fundamentals evidence remains fail-closed and cannot be selected arbitrarily.
- Unknown feature names remain visible in transition counts.
- Missing saved readiness preserves the existing failure behavior.
- No transition changes any exclusion decision or source row.

## No-Write and Product Boundaries

- Reuse the one existing in-memory production readiness build.
- Add no output path, writer, JSON mode, cache, screenshot, report, or timing artifact.
- Do not treat exclusions as negative company signals or investment conclusions.
- Do not convert partial inputs into ready inputs.
- Do not authorize the separately reviewed readiness rebuild.

## Testing and Completion

Test first for behavior-equivalent reason helpers, overlapping matches, transition counts, primary-reason totals, unresolved metadata, and filesystem preservation. Complete when the real preview explains all newly excluded DCF rows or reports an exact unexplained count; focused/full tests and all required product gates pass; exact files are committed and pushed; ROADMAP, methodology/provenance, continuation prompt, and draft PR #113 are updated; generated churn remains zero.
