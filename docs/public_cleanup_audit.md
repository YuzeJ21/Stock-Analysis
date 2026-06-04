# Public Cleanup Audit

## Scope

This audit reviews the current public-branch cleanup before committing it. The goal is to make the repository easier for GitHub and LinkedIn visitors to understand without accidentally removing product-critical documentation, guardrails, examples, or demo data.

## Current Diff Shape

The current diff includes:

- A much shorter public `README.md`.
- A new dashboard preview image at `docs/assets/dashboard-preview.svg`.
- A visitor-friendly `docs/OPERATOR_GUIDE.md` for deeper local workflow commands without re-expanding the README.
- Public naming cleanup from "Stock Research Screener" / "Stock Report Beta" to "Stock Research Command Center" / "Single-Stock Report".
- Removal of tracked internal agent/build instruction files.
- `.gitignore` updates to keep internal agent/build notes out of future public commits.
- Test updates that enforce the public README shape, internal-note exclusion, and research-only guardrails.
- No remaining `data/` or `outputs/` diffs after generated CSV/report churn was restored.

## Removed Items

| Removed item | Classification | Audit note |
| --- | --- | --- |
| `AGENTS.md` | Safe to remove, with preservation caveat | Internal agent instruction file. It contained useful product principles, but those principles are now preserved in `README.md`, `PRODUCT_SPEC.md`, `ROADMAP.md`, and tests. |
| `.agents/skills/stock-analysis-core/SKILL.md` | Safe to remove from public branch | Internal Codex workflow skill. Not needed by visitors to run the product. |
| `.agents/skills/stock-analysis-core/references/*.md` | Safe to remove from public branch, with attribution caveat | Internal build/reference notes, including open-source inspiration mapping and rejected trade-skill behavior. Product-relevant guardrails were preserved publicly. Do not claim "no open source was used"; `docs/PUBLIC_RELEASE_CHECKLIST.md` keeps that warning. |
| Old long `README.md` runbook content | Risky removal, mitigated | The old README had extensive CLI runbooks. The new README intentionally moved to visitor-first documentation. Important basics were retained: product purpose, why readiness matters, quickstart, demo commands, current readiness snapshot, output list, maturity, roadmap snapshot, and research-only guardrails. |

## Safe Removals

- Internal agent/build notes that are not part of the product surface.
- Old public wording that made the app look like a generic screener or beta feature.
- Generated CSV/report churn from `data/` and `outputs/`; these were restored out of the diff rather than committed.

## Risky Or Human-Review Areas

- The removed `.agents` notes included product reasoning and open-source inspiration notes. The product-facing parts were summarized publicly, but a human should confirm they do not want those notes published as development history.
- The README is intentionally shorter. Deeper operator guidance now lives in `docs/OPERATOR_GUIDE.md`; keep future runbook detail there instead of re-expanding the README.
- The repo still tracks sample/local data files. Before sharing publicly, manually review `data/holdings.csv`, `data/fundamentals.csv`, `data/prices.csv`, and example stock reports for personal or sensitive information.
- Add a `LICENSE` file before public sharing if reuse terms matter.
- Existing source/test diffs outside the README/public cleanup are still present on this branch and should be reviewed as product changes, not treated as generated churn.

## Public Docs Health

The current README now answers:

- What the product is: a local CSV-first stock research command center.
- What problem it solves: deciding which analysis is trustworthy today and what data is missing.
- Why data readiness matters: missing data is surfaced as a trust signal instead of hidden.
- How to run a demo: `make pipeline`, `make readiness`, `make stock-report TICKER=NVDA`, `make dashboard`.
- What the dashboard looks like: `docs/assets/dashboard-preview.svg`.
- What the CLI can do: visitor-friendly commands for status, pipeline, reports, dashboard, and targeted unlock queues.
- Where deeper commands live: `docs/OPERATOR_GUIDE.md`.
- What it does not do: no broker integration, order routing, auto-trading, option recommendations, direct buy/sell instructions, or fabricated data.
- What data is ready versus missing: current local readiness snapshot is shown as a local-output baseline.
- Product maturity: working local prototype, not a full-market data provider.

## Broken Reference Check

Checked public Markdown references in:

- `README.md`
- `docs/*.md`
- `PRODUCT_SPEC.md`
- `ROADMAP.md`

Result:

- `README.md` references `docs/assets/dashboard-preview.svg`, and the target exists.
- `README.md` references `docs/OPERATOR_GUIDE.md`, and the target exists.
- Remaining `.agents` / `AGENTS.md` references are intentional exclusion rules in `docs/PUBLIC_RELEASE_CHECKLIST.md` and `tests/test_guardrails.py`.
- No old GitHub owner links, old "Stock Research Screener" title, old "Stock Report Beta" label, or `stock_report_beta` references were found in public docs/source scans.

## Generated CSV/Data Churn Policy

Current status:

- `git diff --name-only data outputs` is empty.
- Generated CSV/report churn should not be committed unless it represents intentional product-facing sample behavior.
- Keep small, useful sample/demo files only when they help visitors run or understand the project.
- Continue ignoring caches, raw downloads, staged imports, generated JSON reports, and local runtime artifacts.

Recommended tracking policy:

- Track source CSV inputs required for the local demo if they are sanitized.
- Track small Markdown examples under `outputs/stock_reports/` if they are useful visitor examples.
- Avoid committing timestamp-only readiness/report rewrites.
- Keep generated `data/reports/` and broad output CSV churn out of public cleanup commits unless the change is intentionally part of the product behavior.

## Fixes Made During Audit

- Added a concise `Why It Matters` README section.
- Added a concise `Maturity` README section.
- Added explicit "not investment advice" wording.
- Added a concise `Roadmap Snapshot`.
- Kept the README compact while restoring the meaning that would otherwise have been lost from the old long runbook.
- Updated README tests to enforce a short visual public landing page while allowing the added trust/maturity context.

## Validation Run

Commands run during the cleanup/audit flow:

- `python3 -m pytest tests/test_launchers.py tests/test_guardrails.py -q`
- `make dashboard-smoke`
- `git diff --check`
- Markdown link/reference checks for README and docs.
- Stale label scans for old repo owner, old app title, old beta label, and old package slug.
- `git diff --name-only data outputs`

Results:

- Public README/guardrail tests passed after updates.
- Dashboard smoke passed.
- `git diff --check` passed.
- No `data/` or `outputs/` diffs remain.
- Full `make test` was attempted earlier but was stopped after staying CPU-active for a long time; do not count it as passed for this audit.

## Public-Readiness Verdict

Public readiness is improved and mostly healthy for a LinkedIn/GitHub visitor. The README is shorter, visual, clearer, and still strong on research-only trust guardrails.

Before final commit/share, human review is still recommended for:

- Whether the internal agent/reference files should remain excluded from the public branch.
- Whether tracked local data and example reports contain anything personal or too specific.
- Whether a `LICENSE` file should be added.
- Whether the current `docs/OPERATOR_GUIDE.md` is enough for the first public share, or should get screenshots after the next dashboard polish pass.
