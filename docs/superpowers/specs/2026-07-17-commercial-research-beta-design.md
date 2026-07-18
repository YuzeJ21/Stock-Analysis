# Commercial Research Beta Foundation Design

## Purpose

Commercial Research Beta turns Personal Research Mode into a controlled, source-backed workflow for repeated company research. It helps a reviewer find changed evidence, understand verified business trends, inspect valuation assumptions, test bounded forward scenarios, maintain a thesis, and choose one next research task. It does not predict stock prices, rank winners, or provide investment instructions.

## Product Contract

The primary path remains **Research Desk -> Discover -> Company Workbench -> Monitor**. Data Health and Proof History remain supporting evidence surfaces. Each primary page must answer one question before exposing detail:

- Research Desk: what changed and what deserves review?
- Discover: which focused-cohort company has usable evidence?
- Company Workbench: what is verified, what is plausible, and what is withheld?
- Monitor: what evidence event or wait condition should be followed?

The beta jobs are daily change review, quarterly business-trend review, valuation scenario review, earnings preparation, thesis/invalidation review, and weekly research closeout.

## Architecture

The beta adds small deterministic contracts around existing systems rather than a second data or analysis stack:

1. A commercial source-rights registry controls which sources may be used in commercial mode.
2. A focused-cohort coverage matrix composes existing readiness into truthful per-company lane states.
3. Existing append-only quarterly actual onboarding remains the canonical Revenue/EPS path; missing real rows fail closed.
4. A Forward View composer combines verified trend, valuation assumptions, reviewed thesis evidence, trusted-peer state, and Earnings Outlook state. It never lets qualitative context mutate numerical inputs.
5. Point-in-time diagnostics preserve current leakage, benchmark, and calibration gates.
6. A refresh-operations contract describes fetch-through-publish state, retry limits, quarantine, freshness, and immutable snapshots without automatically applying or publishing data.
7. Private-beta architecture and pilot measurement remain explicit readiness contracts until external hosting, accounts, and users exist.

## Commercial Source Rights

Every source record contains permitted use, commercial-use state, redistribution state, storage limits, attribution, rate limits, authentication, expected freshness, supported fields, and fallback priority. Commercial mode refuses any source whose commercial-use state is not explicitly approved. Credentials and license documents remain outside Git. SEC evidence remains subject to fair-access requirements; Yahoo/yfinance remains research-only unless separate rights are verified.

## Focused Cohort Truth

The deterministic cohort remains capped at 25 by default and must never exceed 50. A coverage matrix reports price, Revenue, EPS, margins, free cash flow, cash/debt, shares, trusted peers, filing dates, earnings dates, and point-in-time consensus as `usable_now`, `partial`, `candidate_context_only`, `blocked`, or `excluded`. Missing lanes are never padded or converted to an overall ready claim.

## Quarterly Actuals

Only explicit source-backed Revenue and EPS observations are accepted. Each row preserves ticker, fiscal period, period end, report and retrieval timestamps, source reference, currency, scale, accounting basis, and revision lineage. Ambiguous periods, incompatible definitions, post-cutoff observations, unresolved revisions, and inferred quarter values are rejected. Q4 is never annual minus nine months. Operating margin and free cash flow remain withheld until separately versioned source contracts exist.

## Forward View V1

Forward View is an evidence-bound research summary, not a forecast engine. It presents:

1. verified historical trend;
2. supported valuation assumptions and bounded bull/base/bear scenarios;
3. trusted peer context, if available;
4. reviewer-authored catalysts, risks, and invalidation evidence;
5. Earnings Outlook readiness and any calibrated output already allowed by its own gates;
6. withheld fields and one next research task.

Business forecast ranges and valuation scenarios stay separate. Candidate peers, news, generated prose, and model output cannot change Revenue, EPS, DCF, or probability inputs. No numerical Beat/Miss probability appears without the existing calibration gate.

## Operations And Failure States

The refresh lifecycle is `fetch -> normalize -> validate -> quarantine -> preview -> publish snapshot -> rebuild readiness -> detect changes`. Each job records deterministic provider order, schema identity, batch limit, freshness policy, attempt count, status, and failure reason. Identical failed provider paths are not retried within the same session. Automatic application is disabled unless a separately tested lane gate explicitly permits it; this beta foundation does not enable such a gate.

## Private Beta Boundary

Repository-side architecture covers authentication, private workspaces, per-user watchlists and journals, saved scenarios, data separation, secret management, usage/error monitoring, audit logging, retention/deletion, entitlements, and health checks. These are readiness requirements, not implemented claims. Hosting and accounts remain `external_account_required`; real user evidence remains `awaiting_external_review`.

## Validation

Tests must prove commercial-mode source refusal, truthful cohort states, quarterly rejection and preview behavior, Forward View withholding, point-in-time leakage gates, refresh retry/quarantine behavior, and private-beta readiness classification. Desktop and mobile QA must preserve the primary answer, one next action, collapsed Advanced evidence, no horizontal overflow, and visible research-only boundaries.

## Completion Boundary

This foundation is complete when all local contracts, UI integration, docs, and tests pass; external data, rights, hosting, calibration, reviewed peers, and pilot users are precisely classified. It is not commercial launch readiness and must not be described as such.
