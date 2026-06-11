# Public Release Checklist

Use this checklist before sharing the repository on GitHub or LinkedIn.

## README And Visitor Experience

- Keep the top of `README.md` focused on what the project does, why it matters, and how to run it.
- Put the best demo commands near the top: `make demo`, `make status-check TOP_N=5`, `make stock-report-md TICKER=NVDA`, and `make dashboard`.
- Keep `make stock-report TICKER=NVDA` available for optional machine-readable local inspection, but prefer `make stock-report-md` for LinkedIn/GitHub visitors.
- Keep `docs/OPERATOR_GUIDE.md` linked from the README as the deeper local workflow guide so LinkedIn visitors see a short landing page first and advanced users still have exact commands.
- Keep `docs/DATA_STRATEGY.md` linked so visitors understand what can refresh safely, what needs trusted local input, and why the next coverage milestone should be a small pilot.
- Keep the dashboard `Data Health` page visible as the safe freshness guide: read-only routine first, capped price dry-run before real refreshes, and review-required lanes for fundamentals, peers, earnings, and analyst estimates.
- Confirm visitors are not told to manually refresh all 3,538 tickers every day; the public workflow should explain lane-specific freshness and generated-data hygiene instead.
- Keep `make trusted-data-pilot-candidates TOP_N=10` visible as the read-only first step for ranking current company blockers before improving 5-10 trusted companies without broad generated data churn.
- Confirm the default candidate output stays compact for visitors; use `make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` only when local proof file status, decision gates, rejected-row paths, and evidence expectations are needed.
- Keep `make trusted-data-pilot-packet TICKER=CRDO` visible as the one-company before report, review path, validate/apply, rejected-row, and rebuild-proof packet after a candidate is chosen.
- Keep `make trusted-data-pilot TICKERS=<chosen names> TOP_N=10` visible as the follow-up evidence loop after candidates are selected.
- Confirm the pilot output shows the next decision and evidence expectation: proceed only when source proof exists, otherwise keep the ticker visibly blocked by missing data and move to the next candidate.
- Confirm the pilot selection brief is visible: choose 5-10 operating companies only when source proof exists, show the current lane mix, and define a useful pilot win as before report, lane review, trusted source row, validate/preview/apply if rows change, rebuilt readiness, after report, and any still-blocked reason.
- Keep the trusted-data pilot company-focused. Suggested starter set: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`. Treat `QQQ` and `SMH` as ETF/index monitor demos, not operating-company DCF targets.
- Keep the pilot evidence packet visible: baseline readiness, before report, focused blocker check, lane review path, validate/preview/apply, rejected-row check, rebuild proof, and still-blocked evidence row.
- Include current readiness numbers only when they are clearly labeled as local snapshots.
- Keep generated examples that help visitors understand the product, such as `outputs/stock_reports/qqq.md` and `outputs/stock_reports/nvda.md`.
- Keep `docs/METHODOLOGY.md` linked from the README so visitors can see the readiness gates, DCF formula path, peer boundaries, and report-explanation rules.
- Confirm sample stock reports include the visitor scan cue, `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, `Best Review Path`, `Analysis Quality`, `Methodology`, `Evaluation Function Check`, and `Copyable Proof Commands` sections before sharing.
- Review `docs/DIFF_HYGIENE_AUDIT.md` before staging so broad local CSV churn stays out of the public branch.
- Treat new `docs/`, `scripts/`, and `tests/` files from public-product polish as reviewable product candidates, not generated data, when `make diff-hygiene` lists them.
- Avoid committing huge timestamp-only generated CSV churn.

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

- Read `docs/LICENSE_DECISION_GUIDE.md`, then add a root-level `LICENSE` file before claiming the project is open source or granting reuse rights.
- Until a `LICENSE` file exists, describe the repository as a portfolio/demo project rather than reusable open-source software.
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

## Suggested Final Verification

Quick share-safe gate:

```bash
make public-check
```

That gate includes `make public-wording-check`, a read-only scan for unsupported
advice, broker/order execution, auto-trading, options recommendation, or direct
buy/sell instruction language in public-facing surfaces.

After it passes, run `make diff-hygiene` and use only the safe staging
suggestion for intentional product files and reviewed Markdown sample reports.
For a large dirty tree, run `make diff-hygiene-files` and review the ignored
local pathspec lists under `outputs/staging/` before using
`git add --pathspec-from-file=...`. After staging, run
`make staged-hygiene-check` before committing. Leave generated CSV/JSON churn
out unless you intentionally want to publish that artifact.

Expanded command list:

```bash
make pipeline
make readiness
make status-check TOP_N=5
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
