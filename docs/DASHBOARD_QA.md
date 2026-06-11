# Dashboard QA Notes

This file records lightweight browser QA evidence for public-facing dashboard polish.

## 2026-06-06 Main Gap Fix Pass

Checked pages:

- Home: confirmed the Current Data Coverage section renders with the latest local readiness snapshot and copy-only unlock commands.
- Single-Stock Report: confirmed the page renders with ready, blocked, excluded, and copy-only guidance.
- Value / Re-rating: confirmed the page renders valuation readiness language without overclaims.
- Data Health: confirmed the page renders unlock workflow guidance and keeps missing context locked.

Screenshots:

- [Home coverage QA](assets/dashboard-qa-home-coverage.png)
- [Data Health QA](assets/dashboard-qa-data-health.png)

Boundary checked:

- No broker integration, order execution, auto-trading, or direct buy/sell instruction language appeared in the checked pages.
- Commands remain copy-only; the dashboard does not execute refreshes or imports from the UI.

## 2026-06-07 Public Product Flow Pass

Checked pages:

- Home: confirmed the visitor route shows `Review one stock`, `Explore ready names`, and `Improve data coverage`, plus a trusted-data pilot path for improving 5-10 companies first.
- Single-Stock Report: confirmed a local `NVDA` preview renders `At A Glance` followed by `Best Review Path` before detailed tabs.

Boundary checked:

- `Best Review Path` correctly routes the DCF/peer-ready `NVDA` example to review DCF, peers, and source readiness instead of sending it back to price coverage.
- Optional earnings and analyst-estimate context remains locked unless trusted local rows exist.
- Commands remain copy-only; the dashboard does not execute refreshes, imports, broker actions, or trades from the UI.

## 2026-06-07 Follow-Up Product Copy Pass

Checked pages and reports:

- Sidebar: confirmed the main navigation control reads `Choose a page`, not internal review-control language.
- Data Health: confirmed first-screen wording uses checklist/review-path language before advanced command detail.
- Value / Re-rating: confirmed the broad valuation input count is labeled separately from exact company DCF-ready counts.
- Portfolio Review: confirmed table helper copy says `next-step context` instead of engineering-heavy operational wording.
- Trusted Data Pilot: confirmed the read-only pilot prints a company starter set and separates `QQQ` / `SMH` as ETF/index monitor examples, not operating-company DCF targets.
- `outputs/stock_reports/a.md`: confirmed standalone DCF peer wording no longer repeats `DCF assumptions and sensitivity`.

Boundary checked:

- The changes stay copy-only and research-only.
- No generated CSV/JSON churn was published with the UI copy pass.
