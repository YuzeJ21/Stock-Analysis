# Public Release Hygiene

This note summarizes the public-facing cleanup standard for the Stock Research
Command Center. It is meant for maintainers preparing the repository for a
GitHub or LinkedIn share.

## Visitor Experience

- Keep `README.md` short, visual, and focused on what the product does.
- Link deeper workflow detail to `docs/OPERATOR_GUIDE.md`.
- Link methodology detail to `docs/METHODOLOGY.md`.
- Keep dashboard screenshots or preview images under `docs/assets/`.
- Keep sample stock reports only when they demonstrate useful product behavior.

## Data Hygiene

- Treat broad CSV refreshes as local working data by default.
- Do not commit timestamp-only churn from readiness reports or generated output
  CSVs.
- Keep tracked `data/holdings.csv` sanitized as zero-position demo data; do not
  publish real position size, cost basis, account exports, or private thesis
  notes.
- Review tracked sample data before publishing and remove anything personal,
  private, or account-specific.
- Prefer small sanitized examples over large local datasets.

## License Decision

- Current state: no root-level `LICENSE` file is selected, so public reuse rights are not granted yet.
- Visitor-safe wording: describe the repository as a portfolio/demo project
  until a license is chosen.
- Next action: read `docs/LICENSE_DECISION_GUIDE.md`, choose a license path,
  then add `LICENSE` and update the README License section.

## Methodology And Trust

- Explain that readiness gates run before analysis.
- Show DCF assumptions and sensitivity only when trusted inputs are present.
- Keep missing fundamentals, peers, earnings, and analyst estimates visible as
  blockers rather than inferred values.
- Label ETF/index/fund rows as monitor context where operating-company DCF is
  excluded.
- Preserve research-only guardrails as a product strength.

## Public Wording

Safe wording:

- "Project-specific research review logic and application code."
- "Built with the Python data ecosystem."
- "CSV-first implementation with optional provider interfaces."
- "Research-only; no broker integration or order execution."

Avoid wording that overclaims originality, hides dependencies, implies advice,
or suggests trading/execution capability.

## Verification Before Sharing

Run a focused product check before a public update:

```bash
make public-check
make public-wording-check
make demo
make stock-report-md TICKER=NVDA
make stock-report-md TICKER=A
make stock-report-md TICKER=META
make stock-report-md TICKER=QQQ
make stock-report-md TICKER=SMH
make stock-report-md TICKER=APLD
make test
make dashboard-smoke
git diff --check
```

If broader pipeline outputs are regenerated, inspect the diff and commit only
intentional product-facing changes.
