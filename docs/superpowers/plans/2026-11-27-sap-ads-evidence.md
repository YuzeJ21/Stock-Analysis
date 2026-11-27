# SAP Depositary Evidence Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one independent whole-branch review after implementation.

**Goal:** Expose exact SAP native annual EPS and the source ADR ratio in current and saved research while preserving valuation holds.

**Architecture:** Extend existing source observation contracts; add one strict SAP normalized-snapshot validator and reuse current research/Monitor UI. No new source calls or valuation method activation.

**Tech Stack:** Python, existing SEC inline parser, Streamlit HTML projection, pytest and Playwright CI.

**Spec:** `docs/superpowers/specs/2026-11-27-sap-ads-evidence-design.md`

## Global Constraints

- Preserve canonical data, source rights, source receipt times, private records and independent readiness states.
- Exact source uses ADR; do not infer an ADS or USD earnings value.
- Old SAP and all TSM snapshots remain readable. No merge/deployment/people contact.

## Review Focus

- An ordinary EPS value or source ADR ratio must not become USD/ADS earnings or P/E.
- A resealed edited numeric literal must fail normalized snapshot validation.
- Wrong issuer, fiscal period, currency, context, source or promoted flags fail closed.
- Compact UI must display ordinary native EPS when no direct ADS EPS exists.
- Current/saved paths retain exact dates, receipts and no-refetch behavior.

### Task 1: Parse and display the source basis

**Files:** `src/sec_cross_security_policies.py`, `src/sec_selected_security_policies.py`, `src/sec_security_observations.py`, `src/online_peer_valuation_ui.py`, `tests/test_sap_depositary_evidence.py`.

**Interfaces:** Produce a revisioned SAP inspection scope containing three source observations: ADR note/ratio, trading restriction and ordinary native annual diluted EPS. All remain `financial_eligible=False`.

- [x] Write positive source/UI cases and negative wrong-ratio, currency, period and literal cases; observe missing behavior fail.
- [x] Extend only the exact reviewed ratio grammar and numeric token binding; add SAP fact contract and new policy revision.
- [x] Display native ordinary EPS and ratio in compact/full views with continued valuation holds.
- [x] Run the new cases and existing selected-security/observation/valuation tests; verify retained actual source without transport (194 checks passed; exact November 24 source revalidated).

### Task 2: Preserve exact saved evidence, verify and sync

**Files:** new `src/sec_sap_snapshot_evidence.py`; existing `src/online_research_context_store.py`, `src/online_peer_valuation_ui.py`, `src/online_research_tools_ui.py`; new `tests/test_sap_depositary_snapshot.py`; release/goal documentation and targeted browser regression.

**Interfaces:** Consume Task 1's exact scope; produce `saved_sap_numeric_observation_indices(scope, *, context)` (v2 numeric indices, empty tuple for verified legacy notes, `None` for invalid data) and a combined saved-depositary HTML projection. The existing snapshot API/schema and TSM API remain.

- [x] Write save/load projection cases and adversarial resealing cases; observe failure before implementation (28 checks now pass).
- [x] Add the exact-path SAP validator and saved UI integration without broadening the generic raw-token allowance.
- [x] Verify actual save/Monitor/return UI using the existing production functions (Streamlit integration passed; browser cases await CI).
- [x] Recheck the retained fixed cohort using original dates; preserve comparison counts/holds and original input bytes (baseline/final comparisons 4/12, exact replays 5/12).
- [x] Run focused guarded checks, public wording and artifact hygiene; inspect existing source/host/pilot blockers (466 checks passed; no configured host; template has no session evidence).
- [ ] Obtain independent review, resolve material findings, sync a review branch and execute current-revision browser and full engineering CI. Report exact results and blocked later stages.

Independent review completed. Five material findings were reproduced RED→GREEN;
the final focused run passed 466 checks. Sync and current-head CI remain pending.
