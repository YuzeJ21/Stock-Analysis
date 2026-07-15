# Controlled Pilot Review Feedback

Use this template with 5-10 external reviewers after they open the GitHub demo package or the local `demo` profile. It measures product clarity and workflow reliability only. It does not collect market data, validate a source, change readiness, or support an investment conclusion.

## Reviewer Task

Ask the reviewer to follow the public path without operator instructions:

```text
Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History
```

Ask them to use one example ticker and answer these four questions in their own words:

1. Where did you start?
2. What could you use now?
3. What was blocked or excluded?
4. What would you do next?

Do not coach the answers. The purpose is to see whether the public workflow is self-explanatory in under three minutes.

## Optional Task-Based Pilot

After the unassisted three-minute check, use the following tasks when a reviewer can spend another five to eight minutes. Observe first and explain the interface only after the task ends.

1. Find a company with a ready operating-company DCF and identify what can be reviewed now.
2. Find a partial or blocked company and name the most important missing input.
3. Explain why an ETF or index proxy excludes company DCF rather than failing it.
4. Open Proof History and identify the latest evidence outcome without opening raw ledger rows first.
5. Explain what the product must not be used for.

Record the scorecard as workflow evidence only:

| Signal | Allowed value |
| --- | --- |
| Task success | `completed`, `completed_with_help`, or `not_completed`. |
| Moderator help required | `none`, `one_prompt`, or `multiple_prompts`. |
| Readiness comprehension | `correct`, `partial`, or `incorrect` explanation of ready, partial, blocked, excluded, and withheld. |
| Misuse risk | `none`, `uncertain`, or `mistook_as_recommendation_or_live_terminal`. |
| Trust in evidence | `high`, `medium`, or `low`, with a short reason about provenance or blocker clarity. |
| Perceived performance | `responsive`, `noticeably_slow`, or `appeared_frozen`, with the affected route. |
| Repeat-use case | Short research-readiness task they would repeat, or `none`. |

Do not ask whether the reviewer would buy or sell a security. Do not collect a price target, portfolio position, account information, or personal investment decision.

## Capture Sheet

Record one row per review session outside the repository unless the note contains no personal information. Use `docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv` as the copy/paste header when you want comparable rows across 5-10 reviewers; keep the working copy outside Git unless it is intentionally anonymized review evidence.

| Field | Record |
| --- | --- |
| Review label | Anonymous session label such as `R01`; do not use a full name. |
| Review path | GitHub-only or local demo profile. |
| Ticker/example | The example ticker or route the reviewer chose. |
| Where did you start? | Their first page or artifact opened. |
| What could you use now? | Their description of supported analysis or context. |
| What was blocked or excluded? | Their description of withheld or non-applicable analysis. |
| What would you do next? | Their next expected page or action. |
| Time to first answer | Approximate minutes to explain the product state. |
| Confusion point | Exact page, label, or route that caused confusion, if any. |
| Reviewer signal | `clear`, `confused`, `blocked_by_environment`, or `suggestion_only`. |
| Closeout outcome | `clear`, `reproducible_ui_issue`, `documentation_gap`, `environment_limited`, or `intentionally_deferred`. |
| Task scorecard | Record task success, moderator help, readiness comprehension, misuse risk, trust, perceived performance, and repeat-use case only when the optional task pilot was run. |

Do not record names, account details, or investment opinions. Do not ask reviewers for a stock recommendation, price target, trade decision, or personal portfolio information.

## Structured Log Template

Use this local-only copy step when running several reviews:

```bash
cp docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv /tmp/stock-command-center-pilot-feedback.csv
```

Keep the `/tmp` copy or another private working copy outside the repository while collecting feedback. Commit a feedback log only after removing personal information and only when the rows are intentionally reviewed pilot evidence. The template is for product workflow clarity, not data freshness, source proof, or investment conclusions.

## Reproducible Issue Format

Turn only reproducible product issues into backlog items. Use the closeout
outcome field to keep every row actionable without turning all confusion into
product work:

- `clear`: reviewer understood the public workflow.
- `reproducible_ui_issue`: same route, viewport, or wording issue can be reproduced.
- `documentation_gap`: the product worked, but README/walkthrough/share wording was unclear.
- `environment_limited`: browser, local setup, or hosted access prevented review.
- `intentionally_deferred`: valid suggestion, but outside controlled pilot scope.

```text
Route: <public route or document>
Viewport: <desktop or phone>
Observed: <what the reviewer saw>
Expected: <the page question, one answer, or primary next action that was unclear>
Impact: <why this prevented the reviewer from understanding readiness or the next step>
Evidence: <screenshot or exact wording, with no personal information>
```

Prioritize first-viewport, route-order, wording, raw-detail visibility, mobile layout, and accessibility defects. Do not weaken readiness gates merely because a reviewer prefers a faster answer.

## Evidence Boundary

Pilot feedback is not data proof, source proof, or data freshness proof. It cannot unlock prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, metrics, or recommendations.

Keep outcomes distinct:

- `clear`: the workflow was understandable; it does not prove analysis correctness.
- `reproducible_ui_issue`: create a product fix only when the route and observation are recorded.
- `documentation_gap`: fix docs or share copy without changing readiness gates.
- `environment_limited`: the local demo or browser could not be reviewed; do not treat it as a product defect without reproduction evidence.
- `intentionally_deferred`: keep useful suggestions visible without expanding the pilot scope.

After a UI change, rerun `make public-ux-review-notes-check`, `make dashboard-smoke`, `make browser-qa-evidence`, and `make public-check` before updating public screenshots or LinkedIn/GitHub wording.
