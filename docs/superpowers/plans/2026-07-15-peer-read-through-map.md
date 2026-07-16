# Peer Read-Through Map Implementation Plan

1. Add failing core tests for trusted, candidate-only, missing-result, missing-timing, excluded, and deterministic cases.
2. Implement an immutable read-through contract that consumes only stock-report payload evidence.
3. Extend the local provider peer summary with sanitized relationship rows and source-backed peer earnings evidence.
4. Add provider tests that preserve candidate/trusted separation and provenance.
5. Render the map in the existing Valuation tab with technical evidence collapsed.
6. Add focused dashboard tests for plain-language state and no forecast/recommendation mutation.
7. Document the feature in the methodology and authoritative roadmap.
8. Run focused tests, the full suite, public gates, pilot readiness, and hygiene checks.
