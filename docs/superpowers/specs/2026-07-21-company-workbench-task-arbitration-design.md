# Company Workbench Task Arbitration Design

## Purpose

Company Workbench must end with one authoritative research task. A fresh desktop and phone audit found that the current AVGO route can simultaneously say to add point-in-time consensus, add peer mappings, and continue the review or wait. Each statement is locally truthful within its own lane, but together they violate the product promise of one clear next research task.

## Scope

This slice changes task composition and labels only. It does not change readiness, evidence, source rights, forecasts, scenarios, data files, provider access, or ledger contents.

## Decision Contract

Add one pure task-arbitration helper that receives:

- the ticker-scoped research-change answer; and
- the existing ordered Research Conclusion cards.

It returns one immutable task-shaped mapping with title, body, state, and badges. Research Conclusion primary cards declare an existing routing state explicitly: missing price, fundamentals, or peer evidence is `wait_for_evidence`; ETF/context review and full-report review are `review_now`. The arbiter preserves that state and never creates a new readiness or routing vocabulary.

Priority is deterministic:

1. A research change can win only when the change-answer mapping carries the explicit boolean source-backed eligibility field derived from `event.evidence_status == "source_backed"`. An open eligible item keeps its recorded suggested task; a still-blocked item keeps `wait_for_evidence` and its non-empty recorded wait condition (or the existing blocked fallback); an intentionally deferred item keeps `monitor` and its non-empty recorded wait condition (or the existing deferred fallback).
2. Otherwise the first existing Research Conclusion priority wins. That function already orders price, fundamentals, peer evidence, and full-report review without treating optional earnings or estimates as core readiness.
3. If neither input provides a task, return a neutral wait condition without inventing evidence or an action.

The change-answer mapping also carries an explicit context kind with exactly `none`, `snapshot_only`, or `source_backed`. `none` receives a neutral no-queued-change label, `snapshot_only` receives only the snapshot-evidence label, and `source_backed` receives the source-backed label. Snapshot-only items remain visible context, receive no source-backed badge, and never outrank Research Conclusion. The arbiter does not infer context or eligibility from state, text, source reference, or caller shape. It does not inspect candidate context, infer source availability, change deterministic scenarios, or upgrade blocked evidence.

## Presentation Contract

- `Research Conclusion` remains a summary of usable evidence, gaps, and optional context. Its first card is labeled `RESEARCH PRIORITY`, not `NEXT STEP`.
- `Next Research Task` renders only the authoritative arbitration result.
- The Forward View card keeps its lane-specific guidance but is labeled `FORWARD-VIEW LANE UNBLOCK`, not `NEXT RESEARCH TASK`.
- Technical evidence remains under Advanced.
- Desktop and phone layouts remain structurally unchanged.

For the audited AVGO state, the result is one peer-evidence task. The absence of a queued source change remains visible in `What Changed`, while missing consensus remains a Forward View lane unblock rather than a competing overall task.

## Failure And Safety Behavior

- Missing or malformed task inputs produce the neutral wait condition.
- A non-mapping change answer, invalid card collection, non-mapping card, or invalid badge collection fails closed as one whole arbitration input; the helper never skips malformed input to choose a later card.
- Empty change evidence never becomes a fabricated event.
- Optional earnings and analyst-estimate gaps remain lower priority.
- No direct buy/sell wording, post-earnings price prediction, probability, recommendation, broker action, or data mutation is introduced.

## Verification

Tests must prove:

- an explicitly eligible source-backed open change outranks the conclusion priority, while a snapshot-only open change does not;
- no matching change maps to context kind `none`, snapshot-only matching change maps to `snapshot_only`, and eligible source-backed change maps to `source_backed`, with no badge crossover;
- source-backed still-blocked and intentionally deferred changes preserve their routing and wait conditions;
- with no change, the first ordered conclusion priority becomes the one task;
- blocked-input priorities preserve `wait_for_evidence`, while directly reviewable priorities preserve `review_now`;
- empty inputs produce the neutral wait condition;
- Research Conclusion no longer emits a `NEXT STEP` kicker;
- Forward View no longer emits a `NEXT RESEARCH TASK` kicker;
- rendered AVGO Company Workbench contains a scoped no-queued-change card without a snapshot-only badge, exactly one `ONE NEXT TASK` marker with `Add peer mappings`, one `FORWARD-VIEW LANE UNBLOCK`, no retired uppercase `NEXT RESEARCH TASK` kicker, and zero exceptions;
- existing independent readiness and fail-closed tests remain unchanged.

Run focused tests first, then the full repository and all required dashboard, research-render, public, commercial-beta, pilot, whitespace, and hygiene gates.
