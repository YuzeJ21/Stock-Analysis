# Hypothetical Paper-Position Laboratory Design

**Status:** Proposal — not approved; implementation unauthorized

**Date:** 2026-08-12
**Product boundary:** Research-only; data readiness first, analysis second, research decision last

## Decision Summary

This proposal defines a possible future research-rehearsal space where a person could document a hypothetical research plan and later compare that plan with reviewed evidence. It does not authorize a feature, route, database, ledger, schema, migration, fixture, or implementation plan.

The recommended direction is an isolated **Research Rehearsal Lab** rather than a portfolio simulator. The user, not the product, would originate any hypothetical intent. The product would never recommend a security, infer a direction, calculate a position size, propose an allocation, connect to an account, or turn a rehearsal into an executable action.

Owner approval remains required for the product purpose, permitted private data, retention choice, language, threat controls, and acceptance plan. Until every decision is approved, Priority 10 remains blocked and no implementation work may begin.

## Research Purpose And User Workflow

The purpose is to help a researcher test the discipline of a predeclared research process, not the attractiveness or expected return of a security.

A future user journey, if separately approved, would be:

1. enter from a current Company Workbench research context;
2. read the current readiness, evidence, and research-only boundaries before creating anything;
3. author a hypothetical rehearsal statement in the user's own words;
4. record what evidence would support, contradict, or invalidate that statement;
5. set a future evidence-review condition or date;
6. preview the full statement and its privacy/retention treatment;
7. explicitly confirm or discard it; and
8. later review the original statement beside independently preserved evidence without rewriting history.

The laboratory must not appear in Discover eligibility, ranking, Company Brief conclusions, Data Health readiness, Proof History source truth, Monitor priority, deterministic forecasts, outcome calibration, or Public mode.

## Approaches Considered

### A. Isolated research rehearsal — recommended for owner review

Keep the concept as a private, user-authored research-process rehearsal. Do not collect amount, allocation, entry, exit, stop, profit, return, or live-account data. Show reviewed evidence separately and preserve the original wording without scoring it.

This has the smallest misuse surface and the cleanest separation from evidence truth. Its limitation is deliberate: it is not a portfolio simulator and cannot answer performance questions.

### B. Traditional paper portfolio — reject

A conventional paper portfolio would normally invite direction, quantity, notional exposure, entry price, mark-to-market value, profit and loss, and comparison tables. Those behaviors would pull the product toward recommendations, sizing, performance claims, and transaction-like workflows. They conflict with the current product boundary and are outside this proposal.

### C. Hosted collaborative rehearsal — defer

A hosted multi-user variant could support independent review, but it would require verified authentication, workspace isolation, audit storage, retention, deletion, backup, recovery, incident response, and a named operating owner. Those are Priority 6 external gates, not assumptions this design may make.

## Isolation Contract

Hypothetical rehearsal state must remain independent from every authoritative product state:

- it cannot change or satisfy readiness;
- it cannot create source rights, provenance, actuals, consensus, peer, catalyst, or outcome evidence;
- it cannot unlock valuation, forecast, scenario, probability, or calibration output;
- it cannot affect Discover inclusion or ordering;
- it cannot become a Company Brief conclusion or authoritative next research task;
- it cannot change Monitor priority or Data Health counts;
- it cannot appear in Public or Operator proof as authoritative evidence; and
- it cannot be used as training, ranking, recommendation, or performance input.

The laboratory must display saved research evidence and hypothetical user-authored state in visibly separate regions with different labels and identities. Missing or invalid authoritative evidence must stay missing or invalid; hypothetical text can never fill the gap.

## Private-Data Policy

The default policy is data minimization. A future approved feature may collect only what is necessary to preserve the user's own rehearsal and review condition. It must not request or infer:

- legal name, address, contact details, employer, income, net worth, risk tolerance, tax status, account identifier, broker, or custodian;
- live holdings, account balances, transaction history, cost basis, or real order history;
- personally identifiable notes that are unnecessary to the research rehearsal; or
- imported brokerage, email, calendar, or cloud-drive content.

The product must warn users not to enter secrets, credentials, account data, or unnecessary personal information. Free text requires a visible privacy reminder and an owner-approved handling policy before use.

No telemetry, analytics, support export, or model-processing path may receive private rehearsal content unless separately disclosed, minimized, approved, and directly verified.

## Safe Language Contract

Allowed language describes user-authored research process:

- `Hypothetical research rehearsal`
- `User-authored statement`
- `Evidence to review`
- `Invalidation condition`
- `Next evidence review`
- `Not a recommendation or transaction instruction`

Forbidden product language includes or implies:

- model-generated position size;
- recommended allocation;
- buy, sell, hold, add, trim, reduce, long, or short guidance originated by the product;
- broker connection or live-account action;
- order routing or auto-trading;
- entry, exit, stop-loss instruction, or take-profit instruction;
- expected-return, profit-and-loss, win-rate, alpha, or investment-performance claim; or
- a claim that a hypothetical rehearsal proves research quality, predictive skill, suitability, or market readiness.

The product must not rewrite user text into stronger conviction, transaction language, or a directional conclusion. Any future language review must include empty, invalid, adversarial, and ambiguous inputs.

## Misuse And Threat Analysis

| Threat | Failure mode | Required fail-closed response |
| --- | --- | --- |
| Recommendation laundering | User asks the product to choose a security or direction and save it as hypothetical. | Refuse to originate the choice; explain that the user must author a research question and evidence plan. |
| Sizing or allocation laundering | User supplies capital and asks for quantity or portfolio weight. | Do not calculate, store, display, or infer size or allocation. |
| Transaction rehearsal becoming execution | A hypothetical record is linked to a broker, order ticket, alert, or trade command. | No integration surface; live brokerage remains permanently out of scope. |
| Evidence contamination | User-authored text is treated as source proof, readiness, actuals, consensus, peer review, or calibration. | Preserve separate identities and exclude hypothetical state from every evidence/readiness evaluator. |
| Performance marketing | Hypothetical outcomes are aggregated into returns, win rate, alpha, or product claims. | Do not compute or publish performance metrics; review process adherence only if separately approved. |
| Private-data leakage | Free text contains account, identity, employment, or financial data. | Warn before entry, minimize retention, provide deletion, and never expose content through public/share surfaces. |
| Historical rewriting | Later evidence overwrites the original rehearsal. | Preserve the original record and append a clearly separate review if persistence is approved. |
| Automation drift | A future assistant changes the rehearsal, schedules actions, or creates recurring jobs. | Require explicit human confirmation for any durable record; prohibit autonomous follow-up or recurring execution. |

## Storage, Retention, Export, And Deletion Choices

No storage choice is approved by this proposal.

### Choice 1 — Session-only rehearsal

Discard the rehearsal when the session ends. This minimizes privacy and retention risk, but it cannot support later comparison. It is the safest fallback if the owner does not approve durable storage.

### Choice 2 — Explicitly confirmed private local record

Persist only after preview and explicit confirmation in an app-managed private store outside the repository. This could support later review, but only after the app-storage contract, encryption posture, local access boundary, retention period, backup behavior, and deletion verification are approved and implemented independently.

### Choice 3 — Hosted private record

Defer until an actual hosted environment directly proves authentication, workspace isolation, audit, retention, deletion, backup, recovery, incident response, and named ownership.

If durable storage is ever approved, the owner must choose a default retention period. The user must be able to delete one rehearsal and all rehearsals, and the product must verify deletion without implying deletion from independent backups unless that is directly proven. Export, if approved, must be an explicit user action, clearly label all content hypothetical and user-authored, omit secrets and internal identifiers, and never resemble an order ticket or performance report.

## Error And Unavailable States

- When evidence or readiness cannot be verified, the laboratory stays unavailable rather than copying stale or hypothetical state into the gap.
- When private storage cannot be verified, the product offers discard-only session behavior or withholds creation.
- When a preview identity changes, confirmation fails and requires a fresh preview.
- When language violates the safe-language boundary, validation rejects the record without partially saving it.
- When deletion cannot be verified, the product reports deletion unavailable and does not claim success.
- When the user requests recommendation, sizing, allocation, performance, or transaction behavior, the product refuses that behavior while preserving access to ordinary evidence review.

## Acceptance Criteria

Implementation could be considered only after separate owner approval and direct evidence that:

1. the laboratory is isolated from readiness, evidence truth, Discover, Company Brief conclusions, Monitor priority, forecasts, valuation, outcomes, backtesting, and calibration;
2. no route or control originates a recommendation, direction, amount, allocation, entry, exit, stop, profit, or transaction;
3. the user sees the research-only, hypothetical, privacy, retention, and deletion boundaries before confirmation;
4. empty, missing, invalid, stale, conflict, deletion-failure, and unavailable-storage states fail closed;
5. private content never appears in Public mode, repository artifacts, generated readiness data, screenshots, logs, telemetry, or share packages;
6. user-authored and authoritative evidence identities remain visibly and structurally separate;
7. any approved durable record uses preview, explicit confirmation, immutable identity, append-only review history, and verified deletion behavior;
8. independent misuse review attempts recommendation, sizing, performance, evidence-contamination, privacy, and automation attacks;
9. direct human accessibility and privacy review covers the actual environment; and
10. local engineering tests are treated only as engineering evidence, never as source-rights, hosted-operation, human-validation, market, or regulatory proof.

## Explicit Non-Goals

This proposal does not authorize or design:

- routes, components, database tables, schemas, ledgers, migrations, fixtures, APIs, jobs, or an implementation plan;
- real or hypothetical position amounts, notional values, allocations, cash, cost basis, holdings, transactions, or account imports;
- prices for entry, exit, stops, profits, marking, or settlement;
- profit and loss, returns, win rate, alpha, benchmark comparison, attribution, or performance scoring;
- recommendations, rankings, suitability, risk profiling, directional guidance, or expected return;
- broker connections, order routing, alerts that imply action, recurring jobs, or auto-trading;
- provider refresh, canonical-data mutation, readiness activation, generated artifacts, evidence creation, or calibration; or
- public sharing, hosted operation, multi-user collaboration, regulatory claims, or commercial launch.

Live brokerage remains permanently out of scope.

## Owner Decisions Required

Before any implementation planning, the owner must explicitly decide:

1. whether the research-rehearsal purpose is valuable enough to justify a feature at all;
2. whether the name `paper-position laboratory` is safe or should be replaced by `Research Rehearsal Lab`;
3. whether even user-authored direction is prohibited, or permitted only as verbatim user input with no product inference;
4. whether the first approved form is session-only or may use an explicitly confirmed private local record;
5. the exact permitted data, retention duration, export behavior, deletion semantics, and backup statement;
6. whether any model may process private rehearsal text and under what disclosure and minimization contract;
7. the safe-language and refusal contract;
8. the misuse review owner and acceptance evidence;
9. the human accessibility and privacy reviewers; and
10. whether a later implementation plan may be written.

Until those decisions are recorded, implementation remains unauthorized.

## Review Boundary

This document is a proposal for owner review. It is not approval, implementation evidence, legal advice, investment advice, privacy certification, accessibility conformance, hosted proof, user validation, or market validation. No implementation plan follows from this document automatically.
