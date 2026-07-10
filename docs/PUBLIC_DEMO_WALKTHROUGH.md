# Public Demo Walkthrough

Use this when sharing the project from GitHub or LinkedIn. The walkthrough is read-only until you intentionally run local report commands, and it does not refresh broad data or import trusted rows.

## Share Boundary

- Screenshots are product evidence only; they do not prove data freshness or unlock blocked inputs.
- Use `make status-check TOP_N=5` for current coverage and blocker counts.
- Share under the controlled portfolio/demo license; do not describe the repository as open source or reusable software.
- Keep the demo research-only: no investment advice, broker action, order routing, auto-trading, or direct buy/sell instructions.
- No public hosted Streamlit URL is configured yet; the shareable path is the GitHub project, curated screenshots, and tracked `make demo-dashboard` instructions. Use `docs/HOSTED_DEMO_DEPLOYMENT.md` only when preparing a verified hosted app link.
- FMP, Alpha Vantage, and Finnhub are optional provider fallbacks and are not configured by default. Provider setup does not prove coverage until a reviewed source-backed smoke, validation, preview, and readiness rebuild pass.
- Coverage is intentionally readiness-gated rather than complete. Fundamentals, share count, peer mapping, earnings, and analyst estimates can remain blocked or locked while the product is still useful.
- Stop before claiming a blocked lane is ready unless source proof, validation, preview, apply, rebuilt readiness, and proof history all support it.

## Two-Minute External Review Path

- GitHub-only review: start with the preview image, the five-page workflow map, and this walkthrough script.
- Live dashboard review: run `make demo-dashboard`, open `http://localhost:8501/?mode=public`, then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History.
- Evidence boundary: `docs/assets/linkedin-public-dashboard.png` and screenshots show product UI only; `make status-check TOP_N=5` remains the source for current local counts.
- Responsive evidence: desktop and phone-width public-flow checks are summarized in `docs/DASHBOARD_QA.md`; they prove layout behavior, not data freshness.
- Share boundary: controlled portfolio/demo evidence only, not open-source reuse, investment advice, broker integration, or data-freshness proof.

## One-Minute Story

This project is a local research command center. It checks data readiness before analysis, shows what can be reviewed now, and keeps missing or non-applicable analysis visibly locked or excluded.

Best visitor path:

1. Open the README and dashboard preview.
2. Run `make demo` to print the safe walkthrough without changing local data.
3. Run `make demo-dashboard` and open `http://localhost:8501/?mode=public`.
4. Follow the five public pages: Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History.
5. Use the examples below only to show different readiness states.
6. Run `make next-stage` when you want the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder; it is read-only and does not refresh data, import rows, stage files, push, deploy, or expose secrets.
7. Run `make status-check TOP_N=5` only when you want terminal proof of current coverage and blockers.

What each page answers:

| Page | First question | What to show |
| --- | --- | --- |
| Home | What is this product and where do I start? | Readiness-first workflow, next safe action, stop rule. |
| Stock Selector | Which stock can I review? | Readiness-backed queue before one-ticker analysis. |
| Single-Stock Report | What can I use for this ticker right now? | Selected ticker state, usable sections, blocked inputs. |
| Data Health | Why is something blocked and how do I fix it? | One lane answer before proof drawers or raw tables. |
| Proof History | What evidence changed a readiness state? | Evidence-only trail before trusting a changed state. |

## Demo Examples

| Example | What it proves | Good line to point out |
| --- | --- | --- |
| `NVDA` | DCF-ready, source-backed peer context. | Deeper company analysis appears only because the required inputs and mappings are present in the demo snapshot. |
| `MU` | A second DCF-ready, peer-ready company group. | Peer context is distinct from optional earnings and estimate lanes, which remain locked. |
| `ACIC` | Price context with DCF still gated. | The app keeps deeper valuation unavailable rather than filling a missing model input. |
| `AACI` | Fundamentals-blocked company. | The report explains the missing proof boundary instead of inferring data. |
| `SPY` / `QQQ` / `SMH` | Index and ETF monitor context. | Operating-company DCF and peer analysis are excluded, not failed. |

## Local Commands

```bash
make demo                         # print the visitor path without changing local data
make demo-dashboard               # open the compact tracked demo profile
make next-stage                  # print the current package/provider/hosted/source-queue ladder without changing local data

# Optional read-only proof after the app flow is clear:
make status-check TOP_N=5
make stock-report-md TICKER=NVDA
make stock-report-md TICKER=MU
make stock-report-md TICKER=QQQ
make project-status-check
make provider-setup-checklist  # use when project-status-check says source-proof queues are exhausted
```

The dashboard defaults to Public visitor mode. Keep visitors on the five-page path first; switch Public visitor mode off only for Operator context, detailed proof tables, coverage frontier workflows, or validate / preview / apply guidance.

Provider setup is an operator-side follow-up, not a demo prerequisite. If `make project-status-check` says source-proof queues are exhausted, run `make provider-setup-checklist` to see which free/public sources are usable now and which optional keyed providers need local keys. Setup alone does not unlock coverage; readiness still requires source proof, validation, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof history.

Do not open broad proof queues from the public walkthrough. Use the operator guide only after project-status-check shows executable source-backed candidates, new provider data, reviewed manual rows, or changed blockers. Until then, the right public answer is that the product shows the blocked lane and the source boundary instead of inventing a missing input.

## What To Say About Data Gaps

The current sample is intentionally partial. Prices can be refreshed through capped preview-first workflows. Fundamentals, peer inputs, earnings, and analyst estimates require trusted source review before they can unlock deeper analysis.

Missing data is not a product failure here. It is the product's quality control layer.

Pilot packets are still read-only. Local file presence, row counts, staged files, and rejected-row reports are inspection cues, not proof that a lane is ready.

When improving real coverage, snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report. If source proof is unavailable, leave the section blocked and move to the next candidate.

Read the outcome in three states: `Supported` means rebuilt readiness and the regenerated report show the lane is ready; `Still blocked` means validation failed, rejected rows appeared, or the report stayed locked; `Skip` means source proof is unavailable, so no placeholder rows are applied.

## What Not To Claim

- Do not call this investment advice.
- Do not describe the output as a buy/sell system.
- Do not imply broad fundamentals, peer valuation, earnings, or estimates are complete.
- Do not imply there is a public hosted app link until one is deployed and verified.
- Do not imply FMP, Alpha Vantage, or Finnhub provider keys are configured unless they are actually set locally and a reviewed smoke has passed.
- Do not claim blocked sections are negative company signals.
- Do not say the app places orders, has broker integration, or automates execution.

## Strongest Public Message

The project is useful because it refuses to overclaim. It can analyze ready data, explain blocked data, exclude methods that do not fit, and show the exact local proof step required to unlock the next research layer.
