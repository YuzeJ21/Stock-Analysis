# Research Company Dossier Design

## Intent

A researcher should be able to find a saved company, see the evidence boundary, inspect dated source-backed fields, and follow the next research action without reading repeated process prose. The current research screens bury fields and sources under large cards and a single all-modules gate.

## Chosen approach

Reorganize the existing Streamlit research flow. Keep the read-only provider, source-rights, and canonical-data boundaries. A CSS-only repaint was insufficient in the prior pass. A separate frontend would duplicate routing and evidence controls before the source and rights model is settled.

## Product behavior

- Research navigation is a compact task bar: Research Desk, Discover, Company Workbench, Monitor. Public and Operator remain reachable as secondary workspaces.
- Discover puts search and compact results first. Each result shows saved identity, concise saved state, one primary gap, and a direct Workbench action. Long source and blocker context is available on demand. Saved-company population and strict eligibility remain separate.
- Company Workbench starts with a compact company summary and one clear next action. A visible evidence map lists the five existing research lanes, saved state, exact source and period only when recorded, and the missing check otherwise.
- The next research task remains visible. Change history stays in a closed disclosure. The Monitor follow-up panels begin immediately after their heading, with explanatory prose in Advanced evidence.
- The online SEC annual-facts action is visible near the top. Its result keeps source, accession, filing and period dates, direct registered fields, and withheld reasons. It remains a local, read-only inspection and cannot change readiness.
- A cached report is reusable only for the same ticker, provider, data profile, directories, and snapshot identity. An online Operator report cannot appear as saved Workbench evidence.
- Detailed analysis remains accessible in named sections. The interface distinguishes saved local report context from online SEC evidence and does not imply current prices, analyst coverage, reviewed peer relationships, or full U.S. universe coverage.

## Constraints and anti-goals

- No new data import, credentials, provider, recommendation, probability, ranking, or source-rights approval.
- No raw source response or generated data in the reviewed branch.
- Unknown source, date, rights, and field values must be labelled unknown or withheld.
- Keyboard paths, 44 px touch targets, phone width, 200% zoom, and zero horizontal overflow remain required local engineering checks.

## Acceptance

At desktop and phone width, a researcher can search NVDA, open its Workbench, locate the online SEC action and the evidence map without opening one enormous advanced module. The page contains precise fields only after an explicit online check, and every unsupported field stays withheld. Automated tests and live browser checks verify the flow; no human testing claim is made.
