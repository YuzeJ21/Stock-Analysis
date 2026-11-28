# Monitor replay release reconciliation

Reviewed November 28, 2026. The product remains an advanced local research beta.
This stage closes a reproduced test-runtime failure before further feature work.

## Current evidence

PR126 revision `db414bb1` passed 175 SAP/FX checks, all 109 research-journey
checks with six mandatory cases, and 115 release regressions. Its
[full engineering run](https://github.com/YuzeJ21/Stock-Analysis/actions/runs/46078582132)
then completed with **one failure, 10,760 passes and three skips**. The large TSM
desktop snapshot flow found its company in Monitor, then showed the unverified
snapshot warning. Subsequent startup, render, wording and hygiene steps were
skipped because the full suite failed. Those results are not a release pass.

## Reproduced mechanism and correction

The dedicated browser test app used a temporary monkeypatch context for each
Streamlit rerun. An older interrupted rerun could restore the process-global
filesystem root while a newer rerun was between company discovery and loading
that company's snapshots. A deterministic two-thread regression reproduced the
same warning with the real large normalized context and compressed snapshot store.

The fixture now keeps its root and loopback-only socket guards stable for its
dedicated server process, wrapping the original socket functions each time.
Its owner terminates that process for cleanup. The deterministic parent-process
test explicitly restores every patched setting. Production storage, authorization,
snapshot validation and fail-closed error handling have no changes.

Two regressions were observed RED against the previous fixture: overlapping
Monitor reruns lost the snapshot root, and external-denial protection ended when
the rerun returned. Both pass after the correction. Independent review found one important gap:
the repeated-rerun check could not distinguish one original-function wrapper
from nested wrappers. A failing stale-guard sentinel now makes that mutation
fail; the strengthened regression was observed RED then GREEN. The original browser test
still verifies desktop/phone layout, exact context and byte identity, idempotent
save, withheld financial fields, Monitor return route and zero provider traffic.
Runtime and browser cases now run early in release CI as well as the full suite.

The inherited ECB acquisition workflow is pinned to its original PR126 so opening
a later release PR cannot repeat the already-completed source request. The
November23 capture and minimal historical currency-review package remain separate;
no new ECB, SEC or price observations are needed for this repair.

## Completed-frame action measurements

The first repair CI passed the repaired desktop/phone snapshot flow, then failed
the existing refresh-popover check after 113 release passes. Its complete geometry
diagnostic captured the default framework state: height 40, white background,
default foreground and a clipped label on the first unhovered desktop sample.
Later samples in the same test passed. The check had sampled a visible control
before the company compositor finished delivering its styles.

The action tests now wait for the completed script, the final company heading
where applicable, loaded fonts, animation frames and the existing DOM-stability
helper before measurement. Contrast 4.5, minimum 44px height, clipping, rail bounds,
viewport widths, both appearances, hover and actual popover actions are unchanged.
An actual rendered defect still fails those assertions; no visual criterion is
used to decide when measurement can begin. This is measurement readiness, not a
production style relaxation.

## Verification boundary

The next full run passed the Monitor and action repairs but exposed two other
release failures: a cross-industry fixture observation read was empty during a
concurrent write, and the roadmap's status wording placed historical counts next
to a current-status label. That run had 10,761 passes, two failures and three skips;
its separate 175 SAP/FX, 109 journey and 119 release checks passed.

Constructed study/workbench observation files now publish by same-directory
temporary file and atomic replacement. Deterministic reads at the write boundary
were RED for both replacement and first publication; they now see the complete
previous value or an absent initial destination until publication. Encoding
failure preserves the previous bytes and removes the temporary file. No reader
retry or JSON-error suppression was added. Production research persistence is
unchanged. The roadmap identifies its old count explicitly as historical.

The cross-industry browser, observation-boundary and full release-documentation
checks now run in early CI. That expanded job has a 30-minute execution budget;
the full engineering job retains its 90-minute budget and all later checks.
Focused publication, documentation, store and workflow integration passed
171 checks with one existing warning. Exact-head full CI remains required.

The corrected store/tools/workflow integration passed 99 checks; the broader
store, numeric-proof, UI, auth and workflow run passed 160 checks, each with one
existing dateutil warning. A local browser attempt stopped at the sandbox
localhost-bind restriction before launch; no browser pass is inferred from it.
Current-revision declared-runtime desktop/phone,
strict journey, full engineering and subsequent smoke/render checks must be
inspected before this release stage is closed. No new full-suite pass is claimed
until that result exists. Canonical data/output/asset bytes remain protected.

## Next stages

1. Close exact-revision release verification before changing financial behavior.
2. Review remaining vendor issuer identity, security continuity, price adjustment
   and accounting comparability requirements. A later ordinary-share FX review
   does not establish an approved ADS/ADR valuation method or historical availability.
3. Operate the private pilot on an actual permitted host with identity provider,
   private persistence/audit, named owner and directly demonstrated recovery.
4. Complete actual independent researcher sessions and later returns. Existing
   protocols and automated checks cannot substitute for those operating outcomes.

[Execution prompt](goals/MONITOR_RELEASE_RELIABILITY_GOAL.md).
