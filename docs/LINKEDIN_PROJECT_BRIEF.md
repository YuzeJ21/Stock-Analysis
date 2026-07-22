# LinkedIn Project Brief

## Short Version

I built a local Python and Streamlit portfolio beta for evidence-first company research. Its primary workflow is Research Desk -> Discover -> Company Workbench -> Monitor: choose a reviewable company, see what evidence can be used now, keep unsupported conclusions withheld, and monitor source-backed changes.

The product separates the main research answer from technical evidence. Company Workbench brings business trend, valuation, forward context, uncertainty, conclusion, and the next research task into one review surface; Data Health and Proof History remain available when the missing input or provenance is the question.

The main idea remains simple: data readiness first, analysis second, research decision last. Empty or unverified valuation, catalyst, outcome, consensus, and calibration lanes stay withheld rather than displaying fabricated content.

Best first click for the complete product: run the local app and follow Research Desk -> Discover -> Company Workbench -> Monitor. The shorter controlled Public demo remains Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History.

Two-minute external review path:

- GitHub-only review: start with the Workbench answer preview, the four-step Personal Research workflow, and `README.md`.
- Controlled reviewer handoff: send `docs/PILOT_REVIEW_INVITATION.md` for one under-three-minute workflow review before sharing the detailed feedback template.
- Live dashboard review: run `make dashboard`, open `http://localhost:8501/`, then follow Research Desk -> Discover -> Company Workbench -> Monitor. Use `http://localhost:8501/?mode=public` for the five-page controlled demo.
- Hosted app status: no public hosted Streamlit URL is configured yet; share the GitHub project, curated screenshots, and local run instructions unless you separately deploy the app and complete `docs/HOSTED_DEMO_DEPLOYMENT.md`.
- Evidence boundary: `docs/assets/linkedin-public-dashboard.png` is a real Workbench answer-first screenshot; screenshots are product evidence only. Do not publish data-readiness claims from the image.
- Share boundary: controlled portfolio/demo evidence only, not open-source reuse, investment advice, broker integration, or data-freshness proof.
- Coverage boundary: price coverage is broad, but fundamentals, share count, peer mapping, earnings, and analyst estimates still have blocked or locked areas. The product shows those gaps instead of treating them as complete.
- Provider boundary: FMP, Alpha Vantage, and Finnhub are optional local provider fallbacks and are not configured by default. Do not claim full automated fundamentals, estimates, or provider-backed coverage unless a reviewed source path proves it.
- Link boundary: use the stable GitHub repository link only after this reviewed feature reaches the default branch. Until then, keep an existing stable Featured item or label any non-default review link `Draft engineering preview`.

Each research destination opens with a usable answer, a withheld boundary, or a truthful wait state before Advanced Evidence. The four-step workflow and the five-page Public demo are checked at desktop and mobile widths.

Current review status is `share_review_ready` for the local GitHub/demo workflow: deterministic public checks, browser evidence, and repeated local cold/warm route timings pass. External reviewer evidence and hosted-route verification are still unavailable, so this remains a controlled-demo status, not a hosted-product or data-freshness claim.

The first story is company research, not operator automation. Keep reviewed batch packets, provider setup, validate / preview / apply mechanics, and provider-key activation as operator detail after the visitor understands the product.

Operator details stay collapsed until someone intentionally leaves the public path.

Use the reviewed `docs/assets/linkedin-public-dashboard.png` Workbench thumbnail for the LinkedIn Featured card only after the feature is present at the link target.

## Now / Next / Not Yet

Use this framing when someone asks whether the project is ready: it is ready to review as a controlled portfolio demo, while hosting and deeper coverage remain verified next stages.

If someone asks what to do next, run `make next-stage` before opening operator proof queues; it prints the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder without refreshing data, importing rows, staging files, pushing, deploying, or exposing secrets.

| Stage | Answer | Guardrail |
| --- | --- | --- |
| Now | GitHub/LinkedIn portfolio demo with the guided public workflow, screenshots, methodology, and local run commands. | Share the GitHub link and curated screenshot after GitHub is synced and `make public-check` passes. |
| Next | Source-backed Earnings Nowcast evidence pilot, plus optional hosted preview and controlled review. | Keep synthetic fixtures separate from real evidence; do not imply a hosted URL, private access, predictive validation, or provider-backed automation before verification. |
| Not yet | Full hosted data product, complete fundamentals/peer/optional coverage, or provider-backed automation across the universe. | Do not claim complete coverage, data freshness proof, or automated provider-backed readiness. |

## Suggested LinkedIn Post

I built a local Python and Streamlit Stock Research Command Center around one principle:

Data readiness first. Analysis second. Research decision last.

The core workflow is Research Desk -> Discover -> Company Workbench -> Monitor. It helps me choose a reviewable company, bring business trend, valuation, forward evidence, uncertainty, and the next research task into one place, then monitor only source-backed changes.

What matters most is what the product refuses to invent. If actuals, consensus, valuation, catalysts, outcomes, backtesting, or calibration evidence is unavailable, the relevant conclusion stays withheld and the missing proof remains visible. Technical provenance stays under Advanced Evidence unless it is needed to understand the research answer.

What it includes:

- Research Desk for a bounded weekly research queue.
- Discover for readiness-backed company selection without a buy ranking.
- Company Workbench for an answer-first one-company review.
- Monitor for source-backed evidence changes and truthful wait states.
- Advanced Data Health and Proof History for provenance and missing-input review.
- Research-only guardrails: no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions.

This is a local portfolio beta, not a hosted product or market-validated service. The project demonstrates how I approach research workflow, evidence quality, product boundaries, and fail-closed decision support.

GitHub: https://github.com/YuzeJ21/Stock-Analysis

## Copy/Paste LinkedIn Profile Updates

LinkedIn Featured title:

`Stock Research Command Center | Evidence-First Company Research`

LinkedIn Featured description:

`A local Python + Streamlit portfolio project for evidence-first company research. Research Desk -> Discover -> Company Workbench -> Monitor shows what can be used now, what remains withheld, and why. Research-only; no broker integration, auto-trading, or investment advice.`

GitHub About description:

`Readiness-first local stock research dashboard for source-gated analysis workflows`

GitHub topics:

`python`, `research-tool`, `streamlit`, `data-readiness`, `equity-research`, `stock-research`

About-section sentence:

`I also build portfolio projects that turn messy data-readiness problems into guided product workflows, including a readiness-first Stock Research Command Center for equity research review.`

Optional LinkedIn post:

`I have been building a Stock Research Command Center as a local Python and Streamlit portfolio project. The core workflow is Research Desk -> Discover -> Company Workbench -> Monitor: select a reviewable company, see the evidence that can be used now, keep unsupported conclusions withheld, and monitor verified changes. The app stays research-only with no broker integration, auto-trading, order routing, or investment advice. It is a GitHub demo with real product screenshots and local run instructions, not a hosted-product, complete-coverage, or market-validation claim.`

What not to claim:

- Do not call it an investment-advice tool, stock picker, broker integration, execution system, account-action workflow, or data-freshness proof.
- Do not imply blocked fundamentals, peer valuation, earnings, or analyst-estimate lanes are complete.
- Do not describe the repository as open source or reusable software under the current controlled demo license.
- Do not imply there is a public hosted app link until a hosted Streamlit deployment exists and has passed the public share gates.
- Do not imply FMP, Alpha Vantage, or Finnhub provider fallbacks are configured unless local keys are actually set and a reviewed one-ticker smoke has passed.

Featured thumbnail: use `docs/assets/linkedin-public-dashboard.png`. It is a real Workbench answer-first screenshot showing one selected-company answer, usable and withheld evidence, the Data Health handoff, and the stop condition without publishing changing coverage figures. Keep `docs/assets/operator-data-health-metrics-real.jpg` only for deeper operator-mode discussion. The plain GitHub URL card can use GitHub's generated OpenGraph image, so use LinkedIn Featured when you want the curated product screenshot.

LinkedIn can cache older GitHub preview images. If the Featured card still shows the old screenshot after GitHub is pushed, remove and re-add the Featured link, or refresh the URL through LinkedIn's post inspector before adding it again.

## Final LinkedIn Visual Checklist

Use this after the reviewed feature is present at the link target:

1. Open your LinkedIn profile and confirm the Featured card title matches `Stock Research Command Center | Evidence-First Company Research`.
2. Confirm the Featured card description names Research Desk -> Discover -> Company Workbench -> Monitor and keeps the research-only, no-broker, no-auto-trading, and no-investment-advice boundaries.
3. Confirm the Featured image is the reviewed Workbench answer-first screenshot at `docs/assets/linkedin-public-dashboard.png`.
4. If LinkedIn shows a generated GitHub URL card instead, leave it only if you are okay with GitHub's OpenGraph image; otherwise remove and re-add the Featured item with the curated screenshot.
5. Use the stable GitHub repository link only after this feature reaches the default branch. Until then, keep the stable item or label any non-default review link `Draft engineering preview`.
6. Open the GitHub link from LinkedIn and confirm the README starts with `External Reviewer Start Here` and names the GitHub/local-app boundary before deeper operator detail.
7. Stop before claiming screenshots prove current data freshness, changing coverage figures, provider-key activation, hosting, market validation, or investment advice.

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
