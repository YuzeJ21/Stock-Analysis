# Company-first UI and online evidence design — 2026-10-29

## Intent

The personal-research screens make a selected company feel like a static local report. The first view is crowded, Discover puts four alphabetical shortcuts before search, and the Company Brief uses four narrow columns with small type. The intended workflow gives selected-company research a clearer hierarchy and an explicitly dated online source check.

## Approaches considered

- Recolor the existing cards and continue local-only reports: quick, but it leaves search, hierarchy, and freshness confusion intact.
- Replace the application with a new frontend and automatic multi-provider live feed: potentially strongest long-term experience, but it would bypass current source-rights, identity, and readiness boundaries and require a larger product migration.
- **Selected first slice:** improve the existing Streamlit Research Desk, Discover, and Company Workbench hierarchy; connect an explicit server-side SEC annual-facts inspection for the selected company; continue to retain dated evidence. This gives a visible correction and a real online path without implying live prices or changing canonical data.

## Experience

1. Keep the personal-research navigation consistent. The opening area shows the current screen, saved-readiness freshness, and one next action without blank space or repeated boundary text.
2. Discover starts with search. It lists matching saved companies with ticker, inspectable evidence, and the leading gap. Remove the four first-alphabetical-ticker shortcut buttons. Results are evidence-access paths, not rankings or recommendations.
3. Company Workbench opens with a selected ticker/status hero. Use-now and Still-withheld are the primary readable pair; What-changed and Next-task follow below. Core body type should be readable at desktop and phone sizes, with source/stop-rule language preserved. The right status panel must not compete with the primary answer.
4. Show a separate `Check SEC annual facts` action for a selected saved company. A click makes a server-side, one-company, no-cache/no-write request through the existing SEC annual fundamentals preview. A repeated render does not refetch; a new explicit click can refresh. Display retrieval time, SEC CIK and source URL, filing accession/date/period, direct-approved fields, and each withheld reason. If identity, User-Agent, network, period, unit, schema, or rights checks fail, show a bounded unavailable/withheld state.

## Data and rights boundary

Online retrieval is the input step; an immutable dated source receipt is required before canonical use. This first UI result remains an explicitly labelled session-only inspection with retrieval time and source reference. A ticker-to-CIK association is a candidate, not verified issuer/security identity. The SEC Companyfacts API provides filing XBRL facts, not live quotes, consensus, estimates, peers, or a full U.S. universe. Prices and other feeds need separately permitted providers. The action never updates saved readiness, canonical CSVs, rights registry, or investment conclusions. It must not run on every Streamlit rerender or silently promote a field.

## Verification

Use fictional synthetic fixtures for pure presenter and failure tests. Check search-first ordering, accessible labels/links, readable brief layout contract, selected-company scoping, repeated-render no-refetch behavior, User-Agent/network failure states, source and period display, and withheld reasons. Run focused automated tests and desktop/phone browser checks without human testers. Keep generated screenshots and source responses local/ignored. Review branch diff and source rights before any GitHub sync.

## Further stages

Extend official SEC coverage to filing periods beyond the annual preview, with explicit field-level validation. Add a separately reviewed price provider and then estimates/peer sources. Measure issuer domicile, security type, venue and point-in-time coverage before claiming broad U.S. company support. A broader visual redesign can follow once the company-first hierarchy is verified.
