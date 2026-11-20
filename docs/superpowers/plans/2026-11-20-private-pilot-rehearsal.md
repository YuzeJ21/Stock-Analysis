# Private pilot rehearsal plan

The deliverable is a repeatable local Workbench and Monitor rehearsal using two disposable profiles. The existing source registry and private-beta contract determine the remaining operated-pilot gates.

## Acceptance

- Each server uses a fixed profile with the same ticker and issuer in a shared disposable store. Own snapshots and notes reopen. Foreign snapshot routes and cross-scope writes fail verification.
- Workbench and Monitor preserve the exact saved snapshot, section and issuer through both return actions and cold reload on desktop and phone. Source-rights gaps stay visible.
- A simulated provider timeout withdraws the live comparison. Passive reads reuse the hold. An explicit retry recovers from the same constructed source evidence without altering the saved snapshot.
- The previous verified reader reopens both profiles' snapshots. A separate local application switch exercises replay on the previous revision and return to the current revision. Interrupted saves and concurrent retries retain the existing tests.
- Tests write only to disposable stores. Provider transport is barred. Audit and readiness continue to report the hosted authentication, source permission, audit storage and operating-owner gates.

## Files and checks

The recovery tests live in `tests/test_private_pilot_rehearsal.py`. The production-route browser checks and their server fixture live in `tests/test_private_pilot_rehearsal_browser.py` and `tests/private_pilot_rehearsal_fixture.py`. `tests/test_private_pilot_recovery_browser.py` exercises the timeout, held response, explicit retry and saved Monitor replay through the live local UI. A Makefile target runs those cases together with the existing snapshot, notes, authorization, provider and private-beta tests under the protected-artifact guard. The pilot audit and runbook record exact results and scope.

The reader compatibility reference is verified revision `3682b320cf27a2c5b7af84c6d4566e808057a7e5`, whose snapshot code differs from the current implementation. The separate application-switch reference is `c1cb630854bc2e21831d04effef248bf2a640981`, with a distinct Workbench implementation. Previous application files are extracted to private temporary storage. No deployed environment is involved in this local switch.
