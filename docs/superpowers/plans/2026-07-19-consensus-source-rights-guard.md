# Prospective Consensus Source-Rights Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose independent Revenue/EPS commercial source-rights evidence in prospective consensus preview and block unapproved ledger writes only in explicit Commercial Research mode.

**Architecture:** Reuse the immutable commercial source-rights registry and exact-source eligibility decision. Add a pure preview helper that derives required metric scopes from the populated record, keep technical `write_allowed` separate, and make append enforce the combined evidence gate before filesystem mutation when commercial mode is enabled.

**Constraints:** Use temporary pytest paths only; do not collect provider data, run repository record/apply/readiness commands, edit source rights, infer providers, or generate/stage CSV, JSON, report, sample-report, screenshot, or timing churn.

## Task 1: Add failing preview evidence tests

**Files:**

- Modify `tests/test_earnings_consensus_collector.py`

- [ ] Build injected immutable rights fixtures for approved, unverified, and scope-limited sources.
- [ ] Assert approved Revenue and EPS scopes produce independent, deterministic preview evidence.
- [ ] Assert a Revenue-only record does not require EPS scope.
- [ ] Assert a mixed record reports only its missing metric scope.
- [ ] Assert unknown and composite exact sources fail closed without provider inference.
- [ ] Run the focused collector tests and confirm the new contract fails before implementation.

## Task 2: Add failing commercial append tests

**Files:**

- Modify `tests/test_earnings_consensus_collector.py`

- [ ] Assert research mode preserves reviewed local append compatibility.
- [ ] Assert commercial mode blocks an unregistered row before ledger or parent-directory creation.
- [ ] Assert an approved, fully scoped source can append to a temporary ledger in commercial mode.
- [ ] Assert technical rejection remains independently authoritative.
- [ ] Run the focused collector tests and confirm the guard assertions fail before implementation.

## Task 3: Implement preview and pre-write guard

**Files:**

- Modify `src/earnings_consensus_collector.py`

- [ ] Import the existing mode, registry, and eligibility contracts.
- [ ] Derive ordered required fields from populated Revenue/EPS values.
- [ ] Add exact-source rights, supported-scope, evidence-ready, combined-write, and blocker fields to `CollectionPreview`.
- [ ] Preserve existing technical preview states and `write_allowed` meaning.
- [ ] Add optional mode and registry injection to append.
- [ ] Use one registry decision for preview and append.
- [ ] Reject a commercial evidence failure before directory creation or ledger mutation.
- [ ] Keep CLI preview non-writing and make the record command inherit the environment gate.
- [ ] Run the focused collector and source-rights tests and require them to pass.

## Task 4: Durable research and operating contracts

**Files:**

- Modify `ROADMAP.md`
- Modify `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify `docs/DATA_STRATEGY.md`
- Modify `docs/METHODOLOGY.md`
- Modify `docs/PROVENANCE_CONTRACT.md`
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

- [ ] Record the independent Revenue/EPS scope states and explicit commercial pre-write guard.
- [ ] Preserve the research-only append path and all actuals, Q4, split-basis, calibration, synthetic-fixture, and candidate-context boundaries.
- [ ] Record that the checked-in registry still has no approved prospective-consensus source or scope.
- [ ] Record that this local guard is not provider, hosted, reviewer, data-depth, calibration, or market evidence.
- [ ] Update the continuation prompt with the new commit anchor after verified implementation.

## Task 5: Full verification and delivery

- [ ] Run focused collector/source-rights tests.
- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run dashboard smoke and all six Research-route render smokes.
- [ ] Run public wording, public, commercial beta/release, pilot readiness, diff hygiene, and whitespace checks.
- [ ] Verify zero generated churn and no repository consensus write or readiness rebuild.
- [ ] Stage exact intentional files only and pass staged hygiene.
- [ ] Commit and push only `codex/personal-research-mode-mvp`.
- [ ] Update draft PR #113 and verify it remains open and draft.
- [ ] Reassess the next executable gate without claiming source, hosted, reviewer, calibration, operating, or market completion.
