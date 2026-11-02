# NEM SEC evidence review

The authorized slice starts with NEM (CIK 0001164727) in the five-section company page. Explicitly save normalized annual direct SEC facts, replay a saved JSON without transport, compare two saved receipts and show unresolved review items in Monitor. Same inputs are unchanged. Incompatible issuer, duration, concept, units or rights remain gaps. Original data, registry, readiness and process-event counts never change.

Use the existing online annual preview and Companyfacts receipt metadata. Preserve original observation, filing date (publication day, not an invented timestamp), accession, concept, duration, source URL and raw-response SHA-256. Restrict retention to revenue, operating income, operating cash flow and capex under the unchanged registry. Do not retain the complete source response, price data or inferred free cash flow. A portable packet has a content checksum, not a source signature. Imported evidence is user-supplied and not reauthenticated by SEC.

Store explicit captures as immutable generated JSON under ignored outputs/local, scoped to the current profile. A new capture can contain the same source inputs. The last two saved captures form the default comparison. Older pairs can be selected explicitly. Downloads/imports allow clean-checkout replay. Limit import bytes and saved history. Invalid inputs fail visibly. Source-policy changes withhold comparisons rather than imply continued clearance.

## Approaches

Chosen implementation decision: reuse ResearchChangeSnapshot/TickerResearchState and the existing change comparator after field-level comparability gates, with a separate bounded normalized receipt adapter and UI. The old six-company study is fixed to a different scope; extending its pinned reports would misrepresent NEM. A second research journal would duplicate authoring and process counts. These are implementation decisions within the user's execution authorization.

Monitor reads the same profile-scoped evidence captures, displays unresolved data gaps and compatible changes, and links back to NEM research records. It does not create journal records, recommendations, or approval events. Disk persistence is explicit; ordinary page reads and replay never fetch or write.
