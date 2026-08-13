# Stale Readiness Continuation Gate Design

## Problem

The selected default profile is truthfully stale because declared source dates are newer than the saved readiness build. Pilot readiness correctly routes inspection to `make readiness-preview TOP_N=20`, but adjacent read-only operator surfaces still expose conflicting next actions:

- `project-status-check` recommends broad price planning and trusted-data candidate ranking;
- `provider-setup-checklist` reports `sec_fundamentals_share_count` as runnable and sends the operator to `coverage-frontier` even while its own non-retry copy says not to repeat the fundamentals/share-count source ladder;
- `coverage-frontier` presents proof sequences containing `make readiness` without first stating that stale readiness makes those rows planning context only.

These contradictions can restart exhausted provider or coverage loops and can lead an operator toward generated readiness churn despite the active no-write continuation boundary.

## Decision

Add one pure, shared continuation-gate contract derived from the selected-profile `ProfileContext`. Consume it in project status, provider setup, and coverage-frontier rendering.

When readiness is `stale`, the gate reports:

- state: `inspection_only`;
- next safe command: `make readiness-preview TOP_N=20`;
- rebuild boundary: `make readiness` remains a separate intentional reviewed write;
- stop rule: do not start broad refresh, proof, apply, or readiness rebuild work from stale counts.

When readiness is `mixed` or `missing`, the gate remains fail-closed and routes to the same no-write preview, which reports the missing-snapshot condition without writing data. When readiness is `current`, the gate does not override existing source and coverage routing.

## Alternatives Considered

### Documentation-only warning

Rejected because runtime commands would continue to contradict the documentation.

### Project-status-only override

Rejected because provider setup and coverage planning would still expose broader actions and `make readiness` proof sequences without the same gate.

### Shared continuation gate

Selected because one deterministic contract can be tested independently and consumed consistently without changing readiness calculations, source availability, provider rights, canonical data, or generated artifacts.

## Architecture

Create `src/continuation_gate.py` with an immutable `ContinuationGate` value and a pure `build_continuation_gate(ProfileContext)` function.

The gate is presentation and routing evidence only. It does not run the preview, refresh sources, import rows, apply data, rebuild readiness, or claim that the preview makes readiness current.

Consumers:

1. `src/project_status.py`
   - build the selected profile context once in the CLI;
   - print a continuation-safe answer before coverage counts;
   - while the gate is fail-closed, replace broad recommended local commands with the no-write preview and suppress top locked-input action commands that depend on stale readiness counts;
   - keep saved counts visible and explicitly labeled as saved/stale evidence.
2. `src/source_activation_guide.py`
   - override only the current-session action fields when the continuation gate is fail-closed;
   - keep provider availability and external-key classifications visible;
   - make `can_run_now`, `next_step`, and `next_step_reason` agree with the no-write inspection boundary.
3. `src/readiness_ops.py`
   - add the continuation gate to coverage-frontier rendering;
   - keep ranked lanes visible as planning context;
   - state that refresh, apply, proof, and rebuild commands below the gate are not executable while readiness is stale.

## Data And Readiness Boundaries

- `ProfileContext.freshness_state` remains the authoritative selected-profile freshness signal.
- `make readiness-preview TOP_N=20` remains no-write inspection evidence only.
- `make readiness` remains the explicit write-producing rebuild boundary and is never executed by the gate.
- Actuals, consensus, Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, peers, catalysts, outcomes, backtesting, and calibration stay independent.
- No source, provider, key, rights state, candidate, peer, event, forecast, probability, or readiness state is inferred or promoted.

## Error Handling

- Unknown freshness states fail closed to `inspection_required` and the no-write preview command.
- The gate never catches or converts source/data errors into readiness.
- Missing saved readiness remains missing; the preview may return its existing nonzero missing-snapshot status while preserving no-write behavior.

## Testing

1. Unit-test current, stale, mixed, missing, and unknown continuation-gate states.
2. Add project-status tests proving stale output presents the preview first and omits broad price/trusted-data recommendations.
3. Add provider-checklist tests proving stale selected-profile context overrides stale preflight action fields while preserving missing-key classifications.
4. Add coverage-frontier tests proving stale rendering labels ranked rows planning-only and names the separate reviewed rebuild boundary.
5. Run focused tests, the complete repository suite, dashboard and research render smoke, public wording/public checks, commercial-beta checks, pilot readiness, diff hygiene, and staged hygiene.

## Non-Goals

- No readiness rebuild.
- No CSV, JSON, report, sample-report, screenshot, timing, or bytecode output.
- No provider probe, source refresh, import, apply, proof record, or broad coverage run.
- No change to the hosted, reviewer, source-rights, trusted-peer, quarterly-adapter, calibration, or operated-platform external dependency classifications.
