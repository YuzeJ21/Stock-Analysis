# Controlled Pilot Review Feedback

Use this template with 10-20 independent target-persona reviewers after they open a verified controlled delivery path or the local `demo` profile. It measures product clarity and workflow reliability only. Owner-led, automated, fixture, and screenshot sessions do not count. It does not collect market data, validate a source, change readiness, or support an investment conclusion.

Before the session, tell the reviewer what will be observed, that participation is voluntary, that they may stop or withdraw their row, and when the working note will be deleted. Record only an anonymous session label and the minimum product feedback below. A withdrawn row must be deleted from the working log and must not appear in aggregate evidence.

## Reviewer Task

For the Commercial Research Beta, ask the reviewer to follow the current research path without operator instructions:

```text
Research Desk -> Discover -> Company Workbench -> Monitor
```

Ask them to use one example ticker and answer these eight questions in their own words:

1. Where did you start?
2. What could you use now?
3. What was blocked or excluded?
4. What evidence supports one conclusion?
5. What was difficult to author or update?
6. What would you do next?
7. Would you use this workflow again for a real research task?
8. What is the most important missing workflow?

Do not coach the answers. The purpose is to see whether the research workflow is self-explanatory in under three minutes.

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
| Evidence trace | `completed`, `completed_with_help`, or `not_completed` when tracing one conclusion to its source evidence. |
| Authoring friction | `none`, `low`, `medium`, or `high`, with the affected record or step. |
| Repeat-use case | Short research-readiness task they would repeat, or `none`. |
| Repeat-use intent | `yes`, `maybe`, or `no`, with an optional short reason. |
| Most important missing workflow | One reviewer-stated missing workflow, or `none`. |

Do not ask whether the reviewer would buy or sell a security. Do not collect a price target, portfolio position, account information, or personal investment decision.

## Commercial Research Beta Tasks

Use this sequence for the Commercial Research Beta after the reviewer can open
the controlled research workspace:

```text
Research Desk -> Discover -> Company Workbench -> Monitor
```

1. Start at Research Desk.
2. Identify the focused cohort and freshness state.
3. Use Discover to select one reviewable company.
4. Open Company Workbench.
5. Explain what can be used now.
6. Identify one withheld input.
7. Review Business Trend, Valuation, and Forward View boundaries.
8. Use Monitor to determine whether verified evidence changed.
9. State why the product is research-only.

Capture task success, time to first useful answer, readiness comprehension,
evidence tracing, authoring friction, misuse risk, evidence trust,
perceived performance, repeat-use case and intent, and the most important
missing workflow. Do not fabricate reviewer sessions, completion rates, quotes, or findings.
If no reviewer can access a verified delivery path, classify the
stage as `awaiting_external_review` rather than treating local test evidence as
pilot evidence.

## Capture Sheet

Record one row per review session outside the repository unless the note contains no personal information. Use `docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv` as the copy/paste header when you want comparable rows across 10-20 reviewers; keep the working copy outside Git unless it is intentionally anonymized review evidence.

| Field | Record |
| --- | --- |
| Review label | Anonymous session label such as `R01`; do not use a full name. |
| Consent confirmed | `yes` only after the reviewer agrees to the session and minimal anonymous capture. A `no` session does not begin. |
| Consent withdrawn | `yes` requires deletion of the row; do not retain it as evidence. |
| Retention/delete after | The date by which the working row will be deleted unless it becomes intentionally reviewed, anonymized aggregate evidence. |
| Review path | Controlled research workspace or local demo profile. |
| Ticker/example | The example ticker or route the reviewer chose. |
| Where did you start? | Their first page or artifact opened. |
| What could you use now? | Their description of supported analysis or context. |
| What was blocked or excluded? | Their description of withheld or non-applicable analysis. |
| What would you do next? | Their next expected page or action. |
| Time to first answer | Approximate minutes to explain the product state. |
| Confusion point | Exact page, label, or route that caused confusion, if any. |
| Reviewer signal | `clear`, `confused`, `blocked_by_environment`, or `suggestion_only`. |
| Closeout outcome | `clear`, `reproducible_ui_issue`, `documentation_gap`, `environment_limited`, or `intentionally_deferred`. |
| Task scorecard | Record task success, moderator help, readiness comprehension, evidence trace, authoring friction, misuse risk, trust, perceived performance, repeat-use case and intent, and most important missing workflow only when the task pilot was run. |

Do not record names, account details, or investment opinions. Do not record contact details. Do not ask reviewers for a stock recommendation, price target, trade decision, or personal portfolio information. Delete withdrawn rows immediately and delete non-evidence working rows by their recorded retention date.

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
