# Multi-company SEC review implementation plan

Design: docs/PRODUCT_REVIEW_2026-11-03.md and docs/goals/MULTI_COMPANY_REVIEW_GOAL.md. Existing isolated checkout and authorized developer-branch sync are retained. Implement inline with one independent final review.

## Contract

Preserve NEM v1/v2 reads and saves. Add a v3 normalized receipt for other qualified US-GAAP/USD annual Companyfacts observations, with strict SEC association metadata and issuer/source consistency. Existing four fields and missingness rules remain. No archive monetary values, prices, raw source responses or derived values are newly retained. The NEM exact-source check remains NEM-specific.

Keep storage under the existing profile-hashed root, per validated symbol, with 100 receipts per company and a visible 100-company profile limit. Multi-company inventory validates scope and reports a broken company separately, without suppressing readable companies. No silent truncation. Comparison never crosses issuers/profiles/periods. Monitor counts only saved company evidence, not market coverage, journal events or alerts.

## Tasks

1. Write failing tests for generic capture/import, association binding, legacy compatibility, identity/path isolation, basis holds, same inputs unchanged, damaged-company isolation and capacity. Generalize src/sec_research_review.py in place; reuse financial_identity_valid and existing comparator. Keep NEM-specific metadata in its existing adapter.
2. Write failing Streamlit tests for AMD controls, cross-company import rejection, Monitor company selection, return links, field-gap versus baseline counts and offline replay. Extend src/sec_research_review_ui.py and existing company/Monitor hooks only as necessary. Compact receipt labels retain exact times in evidence details.
3. Audit and verify actual AMD, DUK and NEM flows on desktop/phone, save observations explicitly, record real supported/held scope and capture screenshots privately. Update roadmap, method and next-stage goals. No assertion of a real financial revision without two independently changed source observations.
4. Commit implementation and focused results; independent read-only review, test-first fixes if required; final exact-commit full guarded suite, hygiene and browser checks. Preserve data/rights digests. Push existing developer branch and verify remote SHA; report hosted CI separately.

## Review focus

Review legacy byte compatibility, generic ticker/CIK/source/association binding, import spoofing boundaries, per-company path containment and symlinks, damaged-store isolation, capacity enforcement without hidden rows, same-input semantics, NEM exception isolation, Monitor claims and no additional transport on replay.

## Ledger

- Live base 1a3107ff matches origin and is clean; no open branch PR. Official comparator pages refreshed and current-run flow audit begun.
- Ruling: do not require a naturally occurring NEM amendment before independently qualifying other company receipts. Cost: real changed-filing behavior remains an explicit evidence gap; synthetic change tests do not close it.
- Core tests observed 23 expected failures before implementation; the initial legacy/generic core set passed 75 tests. Four new UI tests observed failure before implementation. Expanded regression passed 197 tests with the pre-existing dateutil warning.
- Added and verified route-selection and offline-unregistered replay regressions. No local CSV row or automatic identity transport is needed to replay a qualified saved receipt; local model availability stays false. A numeric-symbol symlink isolation regression failed before repair and passed afterward.
- Real AMD online capture saved twice and compared unchanged with four qualified direct fields. DUK and NEM browser cases, final review, exact-head full validation and sync remain in progress; final results belong to the private stage packet.
