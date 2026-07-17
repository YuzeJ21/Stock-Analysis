# LinkedIn Project Brief

## Short Version

I built a local, CSV-first stock research command center that checks whether a ticker has enough trusted data before showing deeper analysis. The main idea is simple: data readiness first, analysis second, research decision last.

The dashboard and single-stock reports show what can be reviewed now, what is blocked by missing data, what is excluded because the method does not apply, and which trusted local input would unlock the next layer.

Best demos: `NVDA` for DCF-ready company review, `META` for valuation still gated by trusted fundamentals, `QQQ` for ETF/index monitor context, `MU` for standalone DCF with peer valuation still locked, and `CRDO` for a fundamentals-gated proof workflow.

Best first click: open the dashboard preview, then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History.

Two-minute external review path:

- GitHub-only review: start with the preview image, the five-page workflow map, and `docs/PUBLIC_DEMO_WALKTHROUGH.md`.
- Controlled reviewer handoff: send `docs/PILOT_REVIEW_INVITATION.md` for one under-three-minute workflow review before sharing the detailed feedback template.
- Live dashboard review: run `make dashboard`, open `http://localhost:8501/?mode=public`, then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History.
- Hosted app status: no public hosted Streamlit URL is configured yet; share the GitHub project, curated screenshots, and local run instructions unless you separately deploy the app and complete `docs/HOSTED_DEMO_DEPLOYMENT.md`.
- Evidence boundary: `docs/assets/linkedin-public-dashboard.png` and screenshots show product UI only; `make status-check TOP_N=5` remains the source for current local counts.
- Share boundary: controlled portfolio/demo evidence only, not open-source reuse, investment advice, broker integration, or data-freshness proof.
- Coverage boundary: price coverage is broad, but fundamentals, share count, peer mapping, earnings, and analyst estimates still have blocked or locked areas. The product shows those gaps instead of treating them as complete.
- Provider boundary: FMP, Alpha Vantage, and Finnhub are optional local provider fallbacks and are not configured by default. Do not claim full automated fundamentals, estimates, or provider-backed coverage unless a reviewed source path proves it.

Each public page now opens with one question, one short answer, one primary next action, and one stop rule. The public workflow is checked at desktop and mobile widths. The current-page shortcut is visible so visitors know where they are.

Current review status is `share_review_ready` for the local GitHub/demo workflow: deterministic public checks, browser evidence, and repeated local cold/warm route timings pass. External reviewer evidence and hosted-route verification are still unavailable, so this remains a controlled-demo status, not a hosted-product or data-freshness claim.

The first story is the public workflow, not operator automation. Keep reviewed batch packets, provider setup, and validate / preview / apply mechanics as operator detail after the visitor understands the product.

Operator details stay collapsed until someone intentionally leaves the public path.

Use the refreshed `docs/assets/linkedin-public-dashboard.png` thumbnail for the LinkedIn Featured card.

## Now / Next / Not Yet

Use this framing when someone asks whether the project is ready: it is ready to review as a controlled portfolio demo, while hosting and deeper coverage remain verified next stages.

If someone asks what to do next, run `make next-stage` before opening operator proof queues; it prints the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder without refreshing data, importing rows, staging files, pushing, deploying, or exposing secrets.

| Stage | Answer | Guardrail |
| --- | --- | --- |
| Now | GitHub/LinkedIn portfolio demo with the guided public workflow, screenshots, methodology, and local run commands. | Share the GitHub link and curated screenshot after GitHub is synced and `make public-check` passes. |
| Next | Source-backed Earnings Nowcast evidence pilot, plus optional hosted preview and controlled review. | Keep synthetic fixtures separate from real evidence; do not imply a hosted URL, private access, predictive validation, or provider-backed automation before verification. |
| Not yet | Full hosted data product, complete fundamentals/peer/optional coverage, or provider-backed automation across the universe. | Do not claim complete coverage, data freshness proof, or automated provider-backed readiness. |

## Suggested LinkedIn Post

I built a local Python and Streamlit stock research command center around one principle:

Data readiness first. Analysis second. Research decision last.

Instead of jumping straight to rankings, the project checks whether each ticker has enough trusted local data for the analysis being shown: price, momentum, liquidity, fundamentals, DCF inputs, peer context, earnings, and analyst estimates.

What I like most about the product is that missing data stays visible. If a ticker is not ready for DCF, peer comparison, earnings context, or analyst-estimate context, the dashboard says why and shows the next local proof step. If a method does not apply, such as operating-company DCF for an ETF/index proxy, the report labels it as excluded instead of failed.

What it includes:

- A Streamlit command center dashboard.
- Market-wide readiness checks across a broad ticker universe.
- Single-stock Markdown reports with At A Glance, Reader Guide, Evaluation Snapshot, Proof Checklist, and Best Review Path sections.
- DCF-ready, standalone DCF, price/setup-only, monitor-only, and data-needed-before-analysis report modes.
- Source readiness notes and copyable local proof commands.
- Lane-level readiness operations and reviewed batch packets for capped, proof-first data work.
- CSV-first import, validation, preview, rejected-row, and readiness workflows.
- Research-only guardrails: no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions.

The most important design choice was refusing to present every ticker as complete. The product is useful because it refuses to overclaim: ready data can be analyzed, blocked data is explained, and missing rows are treated as the next proof step.

GitHub: https://github.com/YuzeJ21/Stock-Analysis

## Copy/Paste LinkedIn Profile Updates

LinkedIn Featured title:

`Stock Research Command Center | Readiness-First Stock Research Workflow`

LinkedIn Featured description:

`A Python + Streamlit portfolio project that checks stock data readiness before showing analysis. It separates ready, partial, blocked, and excluded states, keeps source-proof gaps visible, and stays research-only with no broker integration, no auto-trading, and no investment advice.`

GitHub About description:

`Readiness-first local stock research dashboard for source-gated analysis workflows`

GitHub topics:

`python`, `research-tool`, `streamlit`, `data-readiness`, `equity-research`, `stock-research`

About-section sentence:

`I also build portfolio projects that turn messy data-readiness problems into guided product workflows, including a readiness-first Stock Research Command Center for equity research review.`

Optional LinkedIn post:

`I have been building a Stock Research Command Center as a portfolio project. The core idea is simple: data readiness first, analysis second, research decision last. The app checks whether stock data is ready before showing analysis, separates ready / partial / blocked / excluded states, and keeps source-proof gaps visible when inputs are missing. It is built with Python and Streamlit, and stays research-only: no broker integration, no auto-trading, no order routing, and no investment advice. The public share is a GitHub demo with real product screenshots and local run instructions, not a claim that every coverage lane is complete. This project reflects the kind of data-product work I care about: turning messy coverage, quality, and workflow problems into a guided user experience.`

What not to claim:

- Do not call it an investment-advice tool, stock picker, broker integration, execution system, account-action workflow, or data-freshness proof.
- Do not imply blocked fundamentals, peer valuation, earnings, or analyst-estimate lanes are complete.
- Do not describe the repository as open source or reusable software under the current controlled demo license.
- Do not imply there is a public hosted app link until a hosted Streamlit deployment exists and has passed the public share gates.
- Do not imply FMP, Alpha Vantage, or Finnhub provider fallbacks are configured unless local keys are actually set and a reviewed one-ticker smoke has passed.

Featured thumbnail: use `docs/assets/linkedin-public-dashboard.png`. It is a real product screenshot of the public visitor path; use `make status-check TOP_N=5` for current local readiness counts because screenshot counts can become stale after local refresh/import work. Keep `docs/assets/operator-data-health-metrics-real.jpg` only for deeper operator-mode discussion. The plain GitHub URL card can use GitHub's generated OpenGraph image, so use LinkedIn Featured when you want the curated product screenshot.

LinkedIn can cache older GitHub preview images. If the Featured card still shows the old screenshot after GitHub is pushed, remove and re-add the Featured link, or refresh the URL through LinkedIn's post inspector before adding it again.

## Final LinkedIn Visual Checklist

Use this after GitHub is synced:

1. Open your LinkedIn profile and confirm the Featured card title matches `Stock Research Command Center | Readiness-First Stock Research Workflow`.
2. Confirm the Featured card description says the project is research-only and mentions no broker integration, auto-trading, or investment advice.
3. Confirm the Featured image is `docs/assets/linkedin-public-dashboard.png` when you want the curated product screenshot.
4. If LinkedIn shows a generated GitHub URL card instead, leave it only if you are okay with GitHub's OpenGraph image; otherwise remove and re-add the Featured item with the curated screenshot.
5. Confirm the link target is GitHub unless you have intentionally deployed a hosted Streamlit app.
6. Open the GitHub link from LinkedIn and confirm the README starts with `External Reviewer Start Here` and names the GitHub/local-app boundary before deeper operator detail.
7. Stop before claiming screenshots prove current data freshness, coverage completion, provider-key activation, or investment advice.

## Resume Bullet Options

- Built a Python and Streamlit stock research command center that evaluates market-wide ticker readiness before generating research decisions.
- Designed a CSV-first data pipeline covering price, momentum, liquidity, correlation, fundamentals, DCF, peer mapping, earnings, and analyst-estimate readiness.
- Implemented readiness-aware decision outputs that separate `Research Now`, `Monitor`, and `Blocked by Data` states with explicit blockers and next actions.
- Added single-stock At A Glance, Reader Guide, Evaluation Snapshot, Proof Checklist, Best Review Path, Analysis Quality, Methodology, Evaluation Function Check, and Copyable Proof Commands sections to explain whether each report supports DCF-ready review, standalone DCF review, monitor-only context, price/setup review, or data-needed-before-analysis work, with the valuation boundary and DCF method path visible before detailed report tables.
- Added source readiness checks, preview-first local import validation, rejected-row reporting, and research-only guardrails to prevent overclaims.
- Documented which parts are original analysis rules, which parts are support libraries, and which actions remain permanently out of scope.
- Created deterministic tests for report wording, dashboard helpers, readiness gates, decision consistency, and no broker/order/trading language.

## Demo Talking Points

- In GitHub, start with the README example map and click the tracked sample reports under `outputs/stock_reports/`.
- Use `docs/PUBLIC_DEMO_WALKTHROUGH.md` as the short live-demo script.
- Start with `make status-check TOP_N=5` to show the read-only command-center summary without refreshing local artifacts.
- Open `outputs/stock_reports/nvda.md` to show a company report with At A Glance status, Evaluation Snapshot, Proof Checklist, Best Review Path, method cue, DCF assumptions, DCF formula path, Analysis Quality notes, Methodology, Evaluation Function Check, and Copyable Proof Commands.
- Open `outputs/stock_reports/a.md` or `outputs/stock_reports/mu.md` to show standalone DCF review where peer-relative valuation is still locked; `MU` now shows mapped-peer valuation inputs as the next proof path.
- Open `outputs/stock_reports/meta.md` to show price/setup review where valuation remains gated until trusted fundamentals and DCF inputs are ready.
- Open `outputs/stock_reports/qqq.md` or `outputs/stock_reports/smh.md` to show ETF/index monitor handling where DCF and peer valuation are excluded, not failed.
- Open `outputs/stock_reports/apld.md` or `outputs/stock_reports/crdo.md` to show how the product handles blocked data without inventing valuation conclusions, including the exact copyable local commands for the next proof step and one-company pilot packet.
- Run `make next-stage` before operator proof queues when someone asks what the current safest next move is.
- Run `make project-status-check` first and use `make provider-setup-checklist` when source-proof queues are exhausted.
- Do not run trusted-data pilot queues as a LinkedIn demo talking point unless project-status-check shows executable source-backed candidates.
- Keep lane-level operator views, coverage frontier details, reviewed batch packets, and validate / preview / apply guidance as follow-up context after the public workflow is clear.
- Run `DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10` to preview a copy-only reviewed batch packet with dry-run, capped execution, validation, rollback, and proof fields before intentionally writing packet artifacts.
- Use the one-company evidence packet to explain that a useful coverage win needs before/after proof, source evidence, and a rebuilt report, not just a new CSV row.
- Explain that the pilot is intentionally small: pick 5-10 operating companies where the missing input can be source-reviewed, and leave the rest visibly blocked by missing data until trusted rows exist.
- Mention that `QQQ` and `SMH` demonstrate monitor context; the company pilot should use operating-company tickers.
- Run `make dashboard` locally and open `http://localhost:8501/?mode=public` to show the clean visitor workflow: Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History. Turn off Public visitor mode only when you want Operator context, coverage frontier details, reviewed batch packets, and validate / preview / apply guidance.
- Point to `docs/METHODOLOGY.md` when someone asks how the analysis is calculated, to `docs/analysis_capability_audit.md` when someone asks what is strong or intentionally limited today, and to `docs/DATA_STRATEGY.md` when someone asks how coverage can improve without fabricating fundamentals, peers, earnings, or estimates.
- Mention that the project is intentionally research-only and does not connect to a broker or place trades.
