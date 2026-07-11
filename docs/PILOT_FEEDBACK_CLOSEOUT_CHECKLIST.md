# Pilot Feedback Closeout Checklist

Use this checklist after 5-10 external reviewers complete the public workflow:

```text
Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History
```

This closeout is product-workflow evidence only. It is not data proof, source proof, data freshness proof, investment advice, broker integration, or a trade instruction.

## 1. Prepare The Working Log

Keep the working feedback log outside the repository:

```bash
cp docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv /tmp/stock-command-center-pilot-feedback.csv
```

Before any reviewed feedback artifact is committed, remove names, account details, investment opinions, price targets, trade decisions, portfolio information, and any other personal information.

## 2. Classify Every Reviewer Row

Each row should end in one of these product outcomes:

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `clear` | Reviewer could explain what is ready, blocked, excluded, and next. | Keep as pilot evidence only. |
| `reproducible_ui_issue` | Same route, viewport, or wording issue can be reproduced. | Fix the product issue, then rerun public gates. |
| `documentation_gap` | Reviewer understood the app after a doc or README clarification. | Update docs, then rerun public wording and public gates. |
| `environment_limited` | Browser, local setup, or hosted access prevented review. | Do not treat as a product defect until reproduced. |
| `intentionally_deferred` | Valid suggestion, but not needed for controlled pilot readiness. | Record the reason and keep sharing boundaries unchanged. |

Do not classify a reviewer preference as a source-proof defect unless it names a missing trusted source row, validate/preview/apply failure, or proof-ledger gap.

## 3. Fix Only Reproducible Product Issues

Fix issues in this order:

1. First-viewport confusion.
2. Hidden or weak primary next action.
3. Raw tables, commands, provider setup, or proof ledgers visible before Advanced.
4. Mobile spacing, text overflow, or route-order confusion.
5. README, walkthrough, or LinkedIn wording that overclaims hosted availability, data freshness, or reuse rights.

Do not expand coverage, add providers, or apply imports from reviewer feedback alone.

## 4. Close The Pilot Feedback Loop

After fixes or classifications:

```bash
make public-ux-review-notes-check
make dashboard-smoke
make browser-qa-evidence
make public-wording-check
make public-check
make diff-hygiene-summary
git diff --check
```

If the checks pass, the GitHub demo can continue to be shared as a controlled portfolio/demo. If the only remaining issues are provider keys, hosted URL setup, or trusted source rows, classify them as external setup or source-gated and move to the next roadmap item.

## 5. Stop Rules

- Stop before claiming hosted availability until a public URL opens and the five-page workflow is verified.
- Stop before claiming new coverage until source proof, validation, preview, rejected-row review, apply decision, rebuilt readiness, and proof history support it.
- Stop before publishing feedback rows if they contain personal information.
- Stop before describing the repository as open source or reusable software unless the license changes.
