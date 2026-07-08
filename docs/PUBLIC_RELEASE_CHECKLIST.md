# Public Release Checklist

Use this checklist before sharing the repository on GitHub or LinkedIn.

## README And Visitor Experience

- Keep the top of `README.md` focused on what the project does, why it matters, and how to run it.
- Confirm `README.md` includes a `Public Share Readiness` section that says GitHub and screenshots are ready, no public hosted Streamlit URL is configured yet, provider keys are optional/missing by default, generated churn stays excluded, and coverage is readiness-gated rather than complete.
- Put the best demo commands near the top: `make demo`, `make status-check TOP_N=5`, `make stock-report-md TICKER=NVDA`, and `make dashboard`.
- Keep `make stock-report TICKER=NVDA` available for optional local report-data inspection, but prefer `make stock-report-md` for LinkedIn/GitHub visitors.
- Keep `docs/OPERATOR_GUIDE.md` linked from the README as the deeper local workflow guide so LinkedIn visitors see a short landing page first and advanced users still have exact commands.
- Keep `docs/DATA_STRATEGY.md` linked so visitors understand what can refresh safely, what needs trusted local input, and why the next coverage milestone should be a small pilot.
- Keep the dashboard `Data Health` page visible as the safe freshness guide: read-only routine first, capped price dry-run before real refreshes, and review-required lanes for fundamentals, peers, earnings, and analyst estimates.
- Confirm the V1 public route set works before replacing the current design in use: `?mode=public&page=home`, `?mode=public&page=stock-selector`, `?mode=public&page=single-stock-report&ticker=NVDA&open=1`, `?mode=public&page=data-health`, and `?mode=public&page=proof-history`.
- Stock Selector is the primary public stock-selection surface. It should show readiness-backed candidates, blockers, next proof steps, and row actions without presenting the queue as a recommendation list.
- Data Health should stay the first coverage-readiness surface: one answer per lane before queue drawers, route maps, advanced evidence details, or proof ledgers.
- Proof History evidence is the public proof-inspection surface. The `Proof History` page should land there rather than shortcutting visitors into a generic Data Health table.
- Operator context should stay collapsed by default and be framed as secondary evidence, not the primary visitor workflow.
- Confirm visitors are not told to manually refresh the full universe every day; the public workflow should explain lane-specific freshness and generated-data hygiene instead.
- Keep `make trusted-data-pilot-candidates TOP_N=10` visible only after `make project-status` shows executable company candidates for ranking current company blockers before improving 5-10 trusted companies without broad generated data churn. If project-status says current source-proof queues are exhausted, start with `make provider-setup-checklist` instead, then run only the listed reviewed one-ticker smoke command before any broader batch.
- Keep `make readiness-ops-center`, `make coverage-frontier TOP_N=10`, and `make reviewed-batch LANE=prices TOP_N=10` visible as the batch-planning path after the visitor understands the trusted-data pilot. These commands should remain copy-only planning/proof workflows, not automatic refresh/apply steps.
- Run `make pilot-readiness-check TOP_N=10` before calling a public/demo pilot ready. It should show GitHub sync, generated-artifact hygiene, readiness freshness, source-proof gates, proof-ledger status, Browser QA screenshot evidence, public-check boundary, and research-only guardrails before the operator chooses a lane.
- Use `make pilot-share-brief` when you want the concise public/demo handoff at `outputs/pilot_share_brief.md`. It does not refresh data or unlock blocked inputs.
- Use `make pilot-readiness-packet` when you want one reviewed Markdown packet for a pilot reviewer. Treat `outputs/pilot_readiness_packet.md` as intentional pilot evidence only; keep broad generated CSV/report churn excluded unless selected separately.
- Confirm the default candidate output stays compact for visitors; use `make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` only when local proof file status, decision gates, rejected-row paths, and evidence expectations are needed.
- Keep `make trusted-data-pilot-packet TICKER=CRDO` visible as the one-company before report, review path, validate/preview gate, apply boundary, rejected-row, and rebuild-proof packet after a candidate is chosen.
- Keep `make trusted-data-pilot TICKERS=<chosen names> TOP_N=10` visible as the follow-up evidence loop after candidates are selected.
- Confirm the pilot output shows the next decision and evidence expectation: proceed only when source proof exists, otherwise keep the ticker visibly blocked by missing data and move to the next candidate.
- Confirm provider setup remains source-gated: No broad coverage batch should run from setup alone. Provider setup is only an activation boundary: it can activate a source, but readiness changes still require validate, preview, rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence. Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.
- Confirm local file status is framed as inspection only: file presence, row counts, staged-folder counts, or rejected-row report existence are not proof until source review, validation, preview, apply boundary, readiness rebuild, and the regenerated report prove the lane changed.
- Confirm the pilot selection brief is visible: choose 5-10 operating companies only when source proof exists, show the current lane mix, and define a useful pilot win as before report, lane review, trusted source row, validate/preview gate, apply boundary if rows change, rebuilt readiness, after report, and any still-blocked reason.
- Keep the trusted-data pilot company-focused. Suggested starter set: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`. Treat `QQQ` and `SMH` as ETF/index monitor demos, not operating-company DCF targets.
- Keep the pilot evidence packet visible: baseline readiness, before report, focused blocker check, lane review path, validate/preview gate, apply boundary, rejected-row check, rebuild proof, and still-blocked evidence row.
- Include current readiness numbers only when they are clearly labeled as local snapshots.
- Keep generated examples that help visitors understand the product, such as `outputs/stock_reports/qqq.md` and `outputs/stock_reports/nvda.md`.
- Use `docs/assets/linkedin-public-dashboard.png` as the LinkedIn Featured thumbnail unless you intentionally want an operator-mode screenshot; treat image counts as illustrative and use `make status-check TOP_N=5` for current local counts.
- Use GitHub as the LinkedIn link target unless a hosted app has been separately deployed and verified. The current public-share package is GitHub plus curated screenshots plus local run instructions.
- Before replacing the GitHub link with a hosted app link, complete `docs/HOSTED_DEMO_DEPLOYMENT.md` and rerun the public gates.
- Confirm the LinkedIn Featured description mentions Python + Streamlit, data readiness before analysis, research-only, no broker integration, no auto-trading, and no investment advice.
- Confirm LinkedIn copy does not imply complete coverage, provider-key activation, public hosted app availability, data freshness proof, or investment recommendations.
- Run `make browser-qa-evidence` before sharing or replacing public screenshots. It shows the current public-share image recommendation, committed asset checks, current real-app capture status, route expectations, and capture boundaries without refreshing data or writing reports.
- Run `make linkedin-share-check` for the final LinkedIn Featured-card checklist. It is read-only: it does not open LinkedIn, upload files, edit your profile, refresh data, stage files, commit, or push.
- Run `make browser-qa-capture-plan` only when you need the real-screenshot capture sequence for replacing GitHub or LinkedIn visuals.
- Confirm any future pending screenshot captures stay labeled as manual capture work; do not use generated thumbnails, GitHub cards, or screenshots with tracebacks as proof of product workflow.
- Keep `docs/METHODOLOGY.md` linked from the README so visitors can see the readiness gates, DCF formula path, peer boundaries, and report-explanation rules.
- Confirm sample stock reports include the visitor scan cue, `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, `Best Review Path`, `Analysis Quality`, `Methodology`, `Evaluation Function Check`, and `Copyable Proof Commands` sections before sharing.
- Review `docs/DIFF_HYGIENE_AUDIT.md` before staging so broad local CSV churn stays out of the public branch.
- Treat new `docs/`, `scripts/`, and `tests/` files from public-product polish as reviewable product candidates, not generated data, when `make diff-hygiene` lists them.
- Avoid committing huge timestamp-only generated CSV churn.
- If `make readiness` or `make pipeline` was run during verification, clean or exclude the broad generated CSV/JSON churn before the public release commit. Keep only intentionally reviewed artifacts such as `outputs/reviewed_batch_packet.md` and `outputs/reviewed_batch_packet.csv` when they demonstrate the reviewed-batch workflow.

## Open-Source And Attribution Hygiene

Do not claim that the project uses no open-source software. A Python project normally depends on open-source packages such as pandas, pytest, Streamlit, or yfinance.

Safe public wording:

- "Project-specific research review logic and application code."
- "Built with the Python data ecosystem."
- "CSV-first implementation with optional provider interfaces."
- "Research-only; no broker integration or order execution."

Avoid public wording that:

- Claims no external packages or libraries were used.
- Claims total originality if the repo includes third-party dependencies, copied snippets, or adapted code.
- Names an inspiration source unless you intentionally want that connection visible.

Internal build-process notes are not part of the public product surface. Keep private planning, automation, and development-helper notes out of the public branch unless you intentionally want to publish that history.

## License And Legal Basics

- Run `make license-status`, then read `docs/LICENSE_DECISION_GUIDE.md` before changing reuse terms.
- The current root `LICENSE` is a controlled portfolio-demo license; describe the repository as a portfolio/demo project rather than reusable open-source software.
- If the goal is visibility only, keep the controlled-demo state explicit in the README: visitors can review the project, but reuse, copying, redistribution, hosted reuse, or adaptation rights are not granted without written permission.
- If the repo includes copied third-party code, keep required attribution and license notices.
- If the repo only uses normal package dependencies, dependency licenses are usually handled through package metadata, but do not hide or misrepresent them.
- Public data sources should be described accurately as data sources, not as proprietary data you created.

## Data And Privacy

- Keep tracked `data/holdings.csv` as a zero-position sample only; do not publish real shares, cost basis, account exports, or personal portfolio notes.
- Remove real account identifiers, emails, API keys, or private notes.
- Keep `.env`, caches, raw downloads, and rejected import files out of GitHub unless they are intentionally sanitized examples.
- Prefer small sample CSVs and Markdown reports over large generated datasets.

## Product Guardrails To Preserve

- No broker integration.
- No order routing.
- No auto-trading.
- No direct buy/sell instructions.
- No options recommendations.
- No fabricated prices, fundamentals, peer mappings, earnings, analyst estimates, valuation inputs, or recommendations.
- No claim that FMP, Alpha Vantage, or Finnhub are configured unless local keys exist and a reviewed one-ticker smoke has passed.
- No claim that the product has a public hosted app link unless a deployment exists and the public share gates pass against that route.
- No claim that incomplete fundamentals, share-count, peer, earnings, or analyst-estimate lanes are ready.

## Suggested Final Verification

Quick share-safe gate:

```bash
make public-check
```

That gate includes `make public-wording-check`, a read-only scan for unsupported
advice, broker/order execution, auto-trading, options recommendation, or direct
buy/sell instruction language in public-facing surfaces. `make public-check` now includes `make license-status`, so the license/reuse boundary is checked in the same share gate before the visitor-demo handoff prints.

After it passes, run `make public-release-package` for the compact package
status, branch status, generated-churn exclusion list, reviewed staging command,
staged inspection commands, and push boundary. Run `make public-release-handoff`
when you want the exact terminal sequence to verify, run the pilot gate, stage
only product files, run staged hygiene, inspect staged filenames, commit, check
branch status, and push. Then run `make diff-hygiene` if you need the full file
list and use only the safe staging suggestion for intentional product files and
reviewed Markdown sample reports. For a large dirty tree, run
`make diff-hygiene-files` and review the ignored local pathspec lists under
`outputs/staging/` before using `git add --pathspec-from-file=...`. After
staging, run `make staged-hygiene-check`, `git diff --cached --check`, and
`git diff --cached --name-only` before committing. Leave generated CSV/JSON
churn out unless you intentionally want to publish that artifact.

Expanded command list:

```bash
make pipeline
make readiness
make public-check
make pilot-readiness-check TOP_N=10
make pilot-share-brief
make pilot-readiness-packet
make browser-qa-evidence
make linkedin-share-check
make browser-qa-capture-plan
make public-release-handoff
make status-check TOP_N=5
make project-status
make provider-setup-checklist
make demo
make trusted-data-pilot-candidates TOP_N=10
make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1  # optional local proof detail
make trusted-data-pilot-packet TICKER=CRDO
make trusted-data-pilot TICKERS=NVDA,CRDO,META TOP_N=10
make stock-report-md TICKER=NVDA
make stock-report-md TICKER=META
make stock-report-md TICKER=QQQ
make stock-report-md TICKER=MU
make stock-report-md TICKER=CRDO
make stock-report-md TICKER=A
make stock-report-md TICKER=SMH
make stock-report-md TICKER=APLD
make test
make dashboard-smoke
git diff --check
```

If `make dashboard-smoke` fails only because the local sandbox cannot bind a port, mention that in the final release notes and verify the dashboard manually on your machine.
