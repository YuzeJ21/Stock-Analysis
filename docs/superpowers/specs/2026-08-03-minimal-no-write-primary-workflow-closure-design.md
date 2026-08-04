# Minimal No-Write Primary Workflow Closure Design

**Status:** Owner-approved scope; primary-only helper amendment pending final owner review.

**Decision date:** 2026-08-03

## Problem

The no-write readiness work correctly moved default research computation toward in-memory results and explicit materialization. Its post-apply command-copy cleanup then expanded into a 45-file migration across primary UI, secondary operator queues, Advanced proof tools, reports, and historical evidence renderers. That expansion increased regression risk without proportionate improvement to the core company-research workflow.

The product still needs a small, enforceable boundary: ordinary Research Desk, Discover, Company Workbench, Monitor, dashboard smoke, validation, and release paths must not silently generate repository CSV, JSON, report, screenshot, or timing artifacts. Explicit operator source mutations and explicit local exports may continue to exist under Advanced controls, but they are not part of the primary workflow and must never be invoked transitively.

## Chosen approach

Use a **minimal primary-workflow closure**.

1. Retain the already committed no-write composition, explicit materializer, profile-bound snapshot/comparison, and protected-artifact guard work.
2. Add one strict primary-only proof-command boundary against compound commands, redirection, arbitrary output arguments, readiness/report/materialization writers, mixed profiles, and non-adjacent apply/comparison sequences.
3. Migrate only copyable actions rendered in the primary Dashboard workflow and the default automatic-policy surface.
4. Add one complete runtime scanner for the deprecated standalone `make readiness` action.
5. Keep secondary operator queues, explicit import/apply tools, Markdown export, proof-ledger recording, and other Advanced surfaces outside this closure. They remain explicit operations and may not be called by default/composite commands.

The discarded alternatives are:

- **Complete the broad 45-file migration:** strongest lexical consistency, but excessive scope, weak incremental user value, and high regression cost.
- **Abandon the no-write boundary:** smaller change, but it would leave recurring artifact churn and make hosted/private-workspace operation less reliable.

## Hard scope cap

The implementation may modify at most these production files:

- `src/reviewed_batch_proof.py` — strict primary-workflow construction and validation of profile-bound proof commands. The existing legacy helper remains unchanged for out-of-scope Advanced callers.
- `src/dashboard.py` — only `single_stock_reader_guide_frame()` and `single_stock_quick_read_cards()`, the primary Company Workbench builders currently capable of rendering reviewed mutation commands. Research Desk, Discover, and Monitor are verification-only unless a test proves they expose the same primary action.
- `src/auto_refresh_orchestrator.py` — default policy and ready-gate commands only.
- `src/readiness_engine.py` — remove the final actionable standalone legacy readiness command.
- `Makefile` — distinguish preview, proof snapshot/comparison, deprecated guard, and explicit Advanced materialization in help text.

The implementation may create or modify only these focused tests:

- `tests/test_reviewed_batch_proof.py`
- `tests/test_readiness_proof_copy.py`
- `tests/test_dashboard_helpers.py`
- `tests/test_auto_refresh_orchestrator.py`
- `tests/test_readiness_command_copy.py`
- `tests/test_launchers.py`
- `tests/test_public_v1_release_docs.py`

This is a 12-file ceiling. Requiring a thirteenth file is a scope failure: record the path and reason in the roadmap instead of expanding the slice.

Within the named production files, the permitted behavior surface is also capped:

- `resolve_readiness_proof_profile()`, `primary_profile_scoped_reviewed_step(*, profile: str, step: str) -> str`, and `primary_profile_bound_reviewed_write_proof_sequence()` in `src/reviewed_batch_proof.py`;
- `single_stock_reader_guide_frame()` and `single_stock_quick_read_cards()` in `src/dashboard.py`;
- `build_default_lane_policies(profile: str | None = None)`, `evaluate_auto_apply_gate(gate, *, profile: str | None = None)`, and selected-profile forwarding through `build_scheduler_plan(..., profile: str | None = None)` in `src/auto_refresh_orchestrator.py`;
- the peer-unlock next-action copy in `src/readiness_engine.py`;
- the readiness help block in `Makefile`.

Changing any other production function is outside this closure even when it contains similar wording.

## Primary behavior

### In-memory default workflow

Ordinary product and validation paths continue to compose readiness in memory. They do not invoke readiness rebuilds, report generators, broad refreshes, source apply commands, screenshots, timing capture, or materialization.

### Copyable proof actions

A copyable primary-workflow apply action must be exactly:

1. profile-bound readiness snapshot;
2. same-profile validation;
3. same-profile preview;
4. same-profile explicitly approved apply;
5. immediate same-profile in-memory comparison.

No readiness rebuild or report/export writer may appear before or after the comparison inside the proof action. A report/export remains a separately labeled explicit Advanced action.

Standalone validate or preview actions may remain copyable when they are bound to the selected profile and proven non-writing. An isolated apply action is never permitted.

The pre-existing `profile_bound_reviewed_write_proof_sequence()` remains a legacy Advanced interface during this closure. Primary Dashboard and automatic-policy code must not call it. Replacing its remaining Advanced callers is explicitly deferred so the strict boundary does not force another broad migration.

### Price profile boundary

Price mutation targets are local-profile only. Primary Dashboard and automatic-policy surfaces render default/demo price writes as unavailable; they never silently switch to local.

### Secondary and Advanced surfaces

Secondary queues and operator tools are not migrated in this closure. They may document explicit source mutation or export commands under Advanced, but:

- the primary Dashboard must not surface them as its recommended action;
- default/composite Make targets must not invoke them;
- their existence does not block this closure unless they are reachable from the primary/default path.

## Error handling and fail-closed rules

- Missing, placeholder, mixed, or unsupported profiles render unavailable.
- Compound commands, shell separators, redirection, output arguments, writer targets, and arbitrary post-comparison tails are rejected by the strict primary boundary.
- Historical command evidence stays non-executable and is not treated as a current instruction.
- Default/demo price writes render the exact local-profile unblock condition.
- A scanner finding outside the hard-capped primary/default path is recorded for the Advanced-surface backlog; it does not expand this slice.

## Verification and acceptance

The slice is complete only when current evidence proves all of the following:

1. Primary-boundary mutation tests reject compound commands, attached or spaced redirection, output arguments, mixed profiles, readiness/report/materialization writers, isolated apply, and writer tails; legacy Advanced helper behavior is unchanged.
2. Rendered primary Dashboard objects under default, demo, and local contain no isolated apply, mixed-profile proof, non-local price write, legacy standalone readiness action, or proof/report combination.
3. Default automatic policies and ready-gate decisions obey the same contract.
4. The runtime scanner finds no actionable standalone `make readiness`; the sole permitted occurrence is the deprecated no-write guard's own help line.
5. Focused tests, the complete test suite, dashboard smoke, public/release/pilot gates, hygiene checks, and `git diff --check` pass.
6. All 124 protected artifact hashes and path/type manifests remain unchanged, with the same 18 pre-existing generated/canonical modifications unstaged.
7. Exact intentional files only are staged. The broad WIP stash is not applied, staged, committed, or pushed.

## Stop rules

- Do not migrate another secondary queue, packet, report, proof-ledger, source guide, or operator console merely for lexical consistency.
- Do not change forecasts, scores, probabilities, readiness semantics, source rights, data providers, or research conclusions.
- Do not run readiness rebuilds, broad refreshes, source applies, generated reports, screenshots, or timing capture.
- Do not exceed the 12-file ceiling.
- If a required acceptance test demonstrates that a thirteenth file is reachable from a primary/default path, stop and request a new scope decision instead of silently expanding.

## Preserved recovery point

The prior broad migration is preserved as Git stash `afabc7a397de8a9434e9da90e2a6cf028d76618f` with message `wip: broad Task 8 proof migration before scope reduction`. It is evidence and recovery material only; it is not an implementation dependency.
