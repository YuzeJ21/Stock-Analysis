# Commercial Price Refresh Enforcement Design

## Status

Approved through the owner-supplied continuation goal on 2026-07-19. This design addresses Priority 1 of the independent internal audit without activating a provider, changing source rights, rebuilding readiness, or generating repository data artifacts.

## Problem

The staged-price import path already keeps technical validity, lineage, exact-source commercial rights, and registered `prices` scope separate. The direct price-refresh path does not use that contract. `make_price_source()` can construct any configured provider, `update_local_price_data()` accepts arbitrary supplied source objects, and successful rows can reach canonical `data/prices.csv` without an exact-source commercial decision.

The root cause is older interface design: `PriceHistorySource` exposes only `fetch_history()`. Operational provider names are display strings, not immutable source identities, and the automatic ladder stores caller-supplied labels without proving they match the underlying source.

## Guardrails

- Research mode retains its current provider ladder, retry, status, and canonical-write behavior.
- Commercial mode fails closed before provider network access when exact-source rights or registered `prices` scope is incomplete.
- Provider aliases used by the CLI may select a provider implementation, but they cannot change or borrow the provider's exact source ID.
- Composite or ladder labels never receive borrowed rights.
- An injected source-rights registry is test and review evidence only; it does not edit `config/source_rights.yml`.
- No source is added to the checked-in rights registry in this slice.
- No provider is called, no broad refresh is run, and no readiness or canonical repository artifact is regenerated.

## Considered Approaches

### 1. Guard only the CLI and Make targets

This would be a small change, but direct Python callers, scheduled orchestration, and injected source objects could still bypass the check. Rejected because the security boundary would remain outside the mutation function.

### 2. Guard only immediately before writing `prices.csv`

This would protect the canonical file, but an unapproved source could still receive credentials, make network calls, and create status output. Rejected because the continuation contract requires refusal before provider execution and before any output mutation.

### 3. Exact identity with defense-in-depth checks

Selected. Every concrete provider exposes one stable exact `source_id`. Commercial construction filters or blocks ladder legs before instantiation. `update_local_price_data()` validates supplied sources before fetch and revalidates the actual selected provider after fetch but before status or canonical mutation. This closes CLI, direct-call, automatic-ladder, and dynamic-source gaps while leaving research mode compatible.

## Design

### Provider identity

Extend `PriceHistorySource` with a required `source_id` string. Concrete source IDs are exact implementation identities:

- `stooq`
- `yahoo`
- `fmp`
- `alpha_vantage`
- `finnhub`
- `ibkr`

These IDs are not inferred from class names, `provider_name`, source messages, environment variables, or aliases. The automatic ladder validates that every route label exactly equals the child's `source_id` and retains the selected child's ID separately from display status.

### Shared commercial decision

Add one price-source review helper that calls `review_commercial_field_scope(registry, source_id, ("prices",))`. Passage requires both:

1. exact-source commercial rights are approved; and
2. the same source record lists `prices` in `supported_fields`.

Failure raises a deterministic precondition error containing the exact source ID, rights status, and missing scope. It never edits registry state.

### Construction boundary

`make_price_source()` receives optional `commercial_mode` and `rights_registry` arguments. When Commercial Research mode is active:

- a requested exact provider is reviewed before its constructor runs;
- an automatic ladder keeps only configured legs that independently pass exact rights and `prices` scope;
- if no leg passes, construction fails before any provider object or network path is used.

Research mode follows the existing provider order and configuration rules.

### Supplied-source boundary

`update_local_price_data()` receives the same optional commercial arguments. Before loading tickers, fetching, or writing status output, it resolves all possible exact source IDs from the supplied source or ladder and requires every reachable leg to pass. A supplied object without a nonblank exact `source_id` fails closed in commercial mode.

### Final selected-provider boundary

After a fetch returns rows, the refresh path resolves the exact provider that produced them. The selected ID must belong to the pre-reviewed immutable set and must still pass the same rights and field-scope decision. This happens before the frame enters the merge set or a success status row is produced. A changed, missing, composite, or unreviewed selected ID raises and leaves canonical and status outputs absent.

### Mutation behavior

The slice does not change canonical file shape or invent row-level lineage. It only prevents unapproved commercial refresh mutation. Price-lineage preservation and atomic staged apply remain separate audit priorities.

## Error Handling

- Blank or missing supplied `source_id`: `commercial_price_source_id_required`.
- Unknown or unapproved exact source: `commercial_price_source_review_required` with the registry status.
- Missing registered `prices` field: `commercial_price_scope_review_required`.
- Ladder label/source mismatch: deterministic `ValueError` during ladder construction.
- Selected provider outside the pre-reviewed set: `commercial_price_source_changed` before mutation.

Errors are local contract failures, not provider availability failures. They do not trigger retries or fallback to an unapproved leg.

## Testing

Tests use temporary directories and injected immutable registries. They must prove:

1. every concrete provider has the expected exact `source_id`;
2. research-mode automatic ladder behavior is unchanged;
3. commercial exact-provider construction blocks unknown, unapproved, and scope-incomplete sources before construction/network use;
4. commercial automatic construction filters independently and fails when no permitted leg remains;
5. supplied sources without identity or approval fail before `fetch_history()` and before data/output directories are created;
6. an approved supplied source with `prices` scope retains the existing refresh result;
7. a source that changes selected identity after fetch fails before canonical or status mutation;
8. focused and full repository tests plus non-writing product and hygiene gates remain green.

## Documentation Boundary

ROADMAP, methodology/provenance documentation, the continuation prompt, and draft PR #113 will record only the verified capability: Commercial Research direct price refresh is blocked unless every reachable and selected exact provider independently passes approved rights and registered `prices` scope. This does not approve a provider, add lineage, activate commercial data, make readiness current, or prove market operation.
