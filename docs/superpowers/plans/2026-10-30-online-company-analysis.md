# Online Company Financial Review Implementation Plan

> Execute inline using the existing worktree and preserve unrelated work.

**Goal:** Let any unambiguous SEC search candidate request a source-bound annual financial review without a local company row or fundamentals file.

**Design:** Keep the existing strict CSV comparison command unchanged by default. An explicit online mode skips canonical and staged-file reads. Reuse the existing SEC field and rights validation, then compose descriptive operating-result, operating-cash-flow, and PP&E spending observations from matching approved direct facts. Show separate unavailable lanes for growth history, live prices, valuation, peers, and forecasts. This is a generic adapter, not evidence that every issuer or security has compatible facts.

**Constraints:** No new credentials, purchases, provider activation, source-rights approval, canonical writes, recommendations, push, PR, merge, deployment, or publication. Derived numeric fields remain withheld. Inputs, source references, annual duration, accession, units, observation, and publication must agree.

1. Reconcile obsolete release-document assertions with the active roadmap and separate authorization for remote release work. Preserve substantive truth checks and concise document budgets.
2. Add failing tests for online mode without CSVs; implement explicit `canonical_path=None` and `staged_path=None` in the no-write preview. Default comparison mode continues to reject missing canonical data.
3. Add failing tests and implement a pure online financial review presenter, using only validated direct fields. Cover negative cash flow, operating losses, mixed identities/periods/units, duplicate fields, missing rights, and nonfinite data.
4. Connect review above field evidence in Company Workbench. Verify desktop, phone, and effective 200% phone layouts and live examples from different sectors, including a ticker absent locally.
5. Update the active roadmap, user guide, and local release packet. Run relevant tests, public wording, hygiene, unchanged-data checks, and commit locally.

**Next expansion:** Measure same-date U.S. listing and issuer gaps; add reviewed historical annual periods and permitted price coverage before valuation. Broaden sectors and taxonomies using explicit coverage evidence. Never equate SEC search presence with U.S. domicile, active listing, or complete research support.
