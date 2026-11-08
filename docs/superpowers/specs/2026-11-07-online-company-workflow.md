# Online company research continuity

The user authorized completing notes, saved evidence and Monitor without preparing local company CSVs, retaining model gaps, automated desktop/phone verification and GitHub synchronization. This implements the online-workflow proposal accepted in the conversation, not a new hosted application or financial method.

## Behavior

- Discover's checked SEC candidate scopes online notes by the actual selected research profile, ticker and nonzero SEC CIK. Reuse the existing preview/confirmation composer and append-only schemas. Private note files are created by an explicit save, with no manual CSV setup.
- Keep online issuer notes separate from legacy saved-workspace notes. Existing profile/ticker records remain readable and writable independently of saved-model construction. Do not silently bind historical ticker-only records to a CIK.
- Persist online records under the ignored `outputs/local/company-research-notes/<profile hash>/<CIK>/<ticker>/` directory. The directory is the saved note scope, not current listing evidence. Validate scope, files, bounds and symlink containment before reopening it. Ordinary reads and previews create no files.
- Different issuer/profile scopes have different widget keys, drafts, previews, confirmations and reload receipts. Ledger rows retain the actual profile key and ticker. Existing unscoped widget keys remain compatible.
- Notes show saved history and user-authored follow-ups. A separate Monitor section discovers these private records, displays company/CIK and review dates and returns to the correct saved or live-session company scope. Reopening a saved note never proves current identity, financial coverage or model eligibility.
- Generic SEC capture/import/replay/comparison remains available without local fundamentals or prices. A specified online CIK must match capture/import/replay; other-issuer receipts are explained separately. Identical observations remain unchanged and incompatible definitions remain gaps.
- NEM/AMD/DUK alone retain the separately qualified exact-pair Reviewed/Still open workflow. Generic saved-company monitoring does not expand that qualification.
- Company Notes never constructs a price-dependent report merely to reach journal controls. Model-dependent Decision Lab, Forward View, scenarios and briefs remain accessible as separately gated saved tools, with one concise unavailable-model explanation.
- Fix the reproduced intermediate-width navigation defect by matching the column-stacking and horizontal-navigation breakpoint. Keep desktop rail and phone two-column cards.

## Boundaries

No canonical financial/readiness/universe data or source-rights changes. No automatic source refresh on section changes or Monitor return. No vendor observation persistence in the new note store. Browser persistence tests use disposable stores and synthetic user records; live checks do not create real research records. No new provider, payment, credentials or hosted workspace deployment.

## Acceptance

1. An online-only synthetic issuer can author/preview/confirm/reopen a thesis and evidence, save two eligible SEC observations, see unchanged comparison, visit Monitor and return with loaded observations and section retained, without local financial or price CSVs.
2. A browser reload can reopen saved issuer notes and saved SEC evidence offline; notes-only companies remain routable. Wrong CIK/profile, corrupt storage and invalid scopes fail closed.
3. Missing local models do not hide notes or SEC controls; retained model tools and their qualification boundaries remain visible.
4. Explicit save checks and immutable SEC source/rights metadata remain unchanged. Disposition allowlist and canonical bytes remain unchanged.
5. Automated unit/integration, real-browser desktop/intermediate/phone checks, source-failure checks and exact-head regression checks pass before GitHub synchronization.
