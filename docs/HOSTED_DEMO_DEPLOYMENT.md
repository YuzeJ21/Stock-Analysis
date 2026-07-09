# Hosted Demo Deployment

Use this only when you want a clickable public app in addition to the GitHub portfolio/demo package. A hosted app is optional; the current public share can remain GitHub plus real screenshots plus local `make dashboard` instructions.

## Current Status

- No public hosted Streamlit URL is configured in this repository.
- GitHub is the public link until a deployment account is intentionally configured and verified.
- Screenshots remain product evidence only; a hosted app does not prove data freshness or unlock blocked inputs.
- The app stays research-only: no investment advice, broker trading, order routing, auto-trading, direct buy/sell instructions, or fabricated data.

For the repo-side readiness check before opening an external hosting account, run:

```bash
make hosted-demo-readiness
```

This command is read-only. It checks the root Streamlit entrypoint, runtime dependency manifest, hosted URL boundary, provider-secret boundary, and public verification commands. It does not deploy, open accounts, print secrets, refresh data, stage files, commit, or push.

## Hosted URL Marker

The repository includes `config/hosted_demo.env.example` as a blank handoff template for a future hosted app URL. Keep the real marker local and untracked:

```bash
cp config/hosted_demo.env.example config/hosted_demo.env
# then set HOSTED_DEMO_URL=https://your-verified-app.example
make hosted-demo-readiness
```

A configured hosted URL is still a manual verification gate. It tells the readiness command which public route to open, but it does not prove the app is live, public-mode-first, source-safe, or share-ready. Do not update README, LinkedIn, or portfolio copy until the hosted URL opens and the five-page public workflow passes the post-deploy smoke checklist below.

## Safe Hosting Boundary

Streamlit Community Cloud or a similar Python app host can run the public dashboard if it can install the `pyproject.toml` dependencies and launch the Streamlit entrypoint used by `make dashboard`.

Set the hosted app entrypoint to `dashboard.py`. The root `dashboard.py` file is a compatibility wrapper around `src.dashboard`, which keeps hosted platforms on a simple root-level Streamlit file while local operators keep using the source module directly. Keep `make dashboard` as the local verification path before and after deployment-specific changes.

Install dependencies from `requirements.txt` or `pyproject.toml`. The root `requirements.txt` contains only runtime app dependencies; optional research/provider extras and broker-style packages stay out of the hosted baseline unless intentionally configured.

## Hosted Setup Values

Use these values when creating a Streamlit Community Cloud app or a similar Python-hosted app. They are setup values only; they do not prove the hosted app exists or that any data lane is fresh.

| Setting | Value | Boundary |
| --- | --- | --- |
| Repository | `YuzeJ21/Stock-Analysis` | Use the same GitHub repo link that is shared in LinkedIn until the hosted URL is verified. |
| Branch | `main` | Deploy only reviewed commits that already passed public gates locally. |
| Main file path | `dashboard.py` | Root compatibility wrapper for `src.dashboard`; do not point hosting at generated reports. |
| Dependency file | `requirements.txt` | Hosted baseline only; optional providers stay behind secrets and smoke tests. |
| Public route | `/?mode=public` | First hosted view must start in public visitor mode, not operator mode. |
| Local health check | `make dashboard-smoke` | Keep local smoke green before debugging hosting-specific behavior. |

Before sharing a hosted URL:

1. Confirm the app opens directly to public mode or clearly routes visitors there.
2. Keep provider keys, account identifiers, tokens, and broker/session files outside the repo.
3. Do not add secrets to committed files, screenshots, sample reports, or generated CSVs.
4. Do not claim FMP, Alpha Vantage, Finnhub, or broker-backed data is active unless the hosted environment actually has the secret configured and a reviewed one-ticker smoke has passed.
5. Do not claim complete coverage; readiness states must continue to show ready, partial, blocked, skipped, and excluded lanes.
6. Run the public gates again after any hosted-app-specific change.

## Secrets And Provider Keys

Local key setup belongs in ignored local files such as `config/provider_keys.env` or in the hosting platform's encrypted secrets UI. The repo should only contain templates and variable names. For hosted Streamlit setup, copy the blank variable names from `.streamlit/secrets.toml.example` into the platform secrets UI; do not commit `.streamlit/secrets.toml`.

Optional provider keys:

- `FMP_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FINNHUB_API_KEY`

Optional broker-style daily OHLCV configuration remains disabled unless explicitly configured for read-only market data:

- `IBKR_HOST`
- `IBKR_PORT`
- `IBKR_CLIENT_ID`

Provider setup is not proof. Readiness changes still require source provenance, validation, preview, rejected-row review, apply or skip decision, rebuilt readiness, and proof-history evidence.

## Verification Before Publishing A Hosted URL

Run these from the repo before changing LinkedIn or README wording to point at a hosted app:

```bash
make hosted-demo-readiness
make public-check
make browser-qa-evidence
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

If the hosted deployment changes app startup, route behavior, or copy, also review the five public pages:

Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History

Stop before publishing the hosted link if the first public view shows tracebacks, raw tables before the answer, command-heavy copy, missing research-only boundaries, or unavailable-provider claims.

## Post-Deploy Smoke Checklist

Run this before replacing the GitHub link in README, LinkedIn, or portfolio copy:

1. Open the hosted root URL and confirm it lands on `/?mode=public` or visibly offers Public visitor mode first.
2. Open `/?mode=public&page=stock-selector` and confirm the selector appears before raw readiness tables.
3. Open `/?mode=public&page=single-stock-report&ticker=NVDA&open=1` and confirm the selected-ticker answer appears before detailed report tables.
4. Open `/?mode=public&page=data-health` and confirm the coverage answer appears before provider setup, commands, or raw proof ledgers.
5. Open `/?mode=public&page=proof-history` and confirm proof history is evidence-only before raw ledger details.
6. Keep the hosted link private if any route shows a traceback, operator mode by default, stale data-freshness claims, or a missing research-only stop rule.

## Link Decision Ladder

Use this ladder before changing README, LinkedIn, or portfolio copy:

| State | Public link to use | Required proof before changing copy |
| --- | --- | --- |
| No hosted URL | GitHub repository link | `make hosted-demo-readiness` reports `external_account_required`; keep local `make dashboard` instructions. |
| Hosted URL opens | Hosted app link can be considered | Open the public URL, confirm the five-page workflow starts in public mode, then rerun `make public-check` and `make browser-qa-evidence`. |
| Provider keys added | Hosted app link plus source boundary note | Run `make provider-setup-checklist` and one reviewed provider smoke; setup alone does not prove coverage or unlock blocked inputs. |
| Hosted route changes copy or layout | Keep GitHub link until rechecked | Re-review Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History and stop if raw tables, tracebacks, or operator commands appear first. |

Do not replace the GitHub link with a hosted link until the hosted app opens successfully, the public path is verified, and the same research-only share gates pass.

## LinkedIn Link Rule

Use the GitHub repository link unless the hosted app exists, has been opened successfully, and has passed the same public-share boundaries. After a hosted app is verified, LinkedIn copy can say "hosted demo available"; until then, keep the wording as "GitHub portfolio/demo project with screenshots and local run instructions."
