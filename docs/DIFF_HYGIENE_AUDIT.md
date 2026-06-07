# Diff Hygiene Audit

Use this note before staging the current public-product polish work. The goal is
to keep the repository visitor-friendly without accidentally committing broad
local data churn.

For a live read-only summary of the current working tree, run:

```bash
make diff-hygiene
make diff-hygiene-summary
make diff-hygiene-files
make staged-hygiene-check
make public-wording-check
```

`make diff-hygiene` classifies the dirty tree and prints safe candidate
`git add` commands for product files and reviewed Markdown sample reports.
`make diff-hygiene-summary` prints the same category counts without long file
lists for the public-share check. `make diff-hygiene-files` writes ignored local
pathspec lists under `outputs/staging/` so long staging commands can be reviewed
before use. `make staged-hygiene-check` inspects the staged diff and fails if
generated CSV/JSON churn or manual-review paths are staged. `make
public-wording-check` scans public docs, dashboard/report copy, preview SVGs,
and sample reports for unsupported advice or execution language while allowing
clear research-only guardrail wording. These commands do not stage, reset,
delete, refresh, or rewrite product data.

The hygiene report shows changed and new file counts. New files under `docs/`,
`scripts/`, and `tests/` are treated as product candidates when they are part of
the public polish work. Review those new files before staging, then keep broad
CSV/JSON output churn out unless a specific generated artifact is the intended
deliverable.

## Current Intentional Change Groups

### Public Visitor Flow

- `README.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/LINKEDIN_PROJECT_BRIEF.md`
- `docs/PUBLIC_RELEASE_CHECKLIST.md`
- `docs/LICENSE_DECISION_GUIDE.md`
- `docs/METHODOLOGY.md`
- `docs/analysis_capability_audit.md`
- `docs/public_cleanup_audit.md`
- `Makefile`

Purpose: shorten the landing page, add a clear demo path, explain methodology,
license status, generated-data hygiene, and research-only guardrails.

### Product UI And Workflow

- `src/dashboard.py`
- `src/project_status.py`
- `src/data_onboarding.py`
- `src/research_health.py`

Purpose: improve dashboard workflow cards, plain-language labels, source and
freshness context, no-refresh-on-load behavior, first-unlock guidance, and
local review next steps.

### Analysis And Report Clarity

- `src/stock_report.py`
- `src/research_decisions.py`
- `src/report_generator.py`
- `src/state_machine.py`
- `src/purpose_evaluation.py`
- `src/purpose_router.py`
- `src/indicators.py`
- `src/momentum_engine.py`
- `src/monthly_picks.py`
- `src/portfolio_review.py`
- `src/loader.py`
- `src/readiness_engine.py`

Purpose: make readiness gates, ATR/volatility provenance, DCF/peer gating,
decision wording, and sample report modes more consistent and less
recommendation-like.

### Intentional Example Reports

- `outputs/stock_reports/a.md`
- `outputs/stock_reports/apld.md`
- `outputs/stock_reports/meta.md`
- `outputs/stock_reports/nvda.md`
- `outputs/stock_reports/qqq.md`
- `outputs/stock_reports/smh.md`

Purpose: keep small visitor-readable examples that demonstrate the main report
modes. These are Markdown examples, not broad generated CSV data.

### Regression Tests

- `tests/test_dashboard_helpers.py`
- `tests/test_launchers.py`
- `tests/test_stock_report.py`
- `tests/test_research_decisions.py`
- `tests/test_pipeline.py`
- `tests/test_classification.py`
- `tests/test_monthly_picks.py`
- `tests/test_project_status.py`
- `tests/test_research_health.py`

Purpose: lock down public wording, no broker/order/trading language, dashboard
row limits, command safety, methodology visibility, report mode consistency, and
readiness-first valuation gates.

## Do Not Stage By Default

Do not stage broad refreshed local data unless it is intentionally selected and
reviewed:

- `data/prices.csv`
- `data/*readiness*.csv`
- `data/reports/*.csv`
- `outputs/*.csv`
- broad timestamp-only CSV churn
- real holdings, account exports, or personal cost-basis files

## Pre-Commit Checks

Run:

```bash
make diff-hygiene
make public-wording-check
git diff --check
git diff --name-only | rg '^(data|outputs)/.*\.csv$' || true
make test
make dashboard-smoke
make demo
make public-check
```

Before staging, inspect:

```bash
git diff --stat
make diff-hygiene
make diff-hygiene-files
make staged-hygiene-check
git diff --cached --stat
git diff --cached --name-only
```

Use the `make diff-hygiene` staging suggestions only after reviewing the listed
files. If the command line is too long to review comfortably, run
`make diff-hygiene-files` and inspect `outputs/staging/product_files.txt` or
`outputs/staging/product_plus_reports.txt` before using `git add
--pathspec-from-file=...`. Run `make staged-hygiene-check` after staging and
before committing. The staged diff should include intentional code, docs, tests,
and small Markdown sample reports only.
