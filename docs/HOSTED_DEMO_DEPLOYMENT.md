# Hosted Demo Deployment

Use this only when you want a clickable public app in addition to the GitHub portfolio/demo package. A hosted app is optional; the current public share can remain GitHub plus real screenshots plus local `make dashboard` instructions.

## Current Status

- No public hosted Streamlit URL is configured in this repository.
- GitHub is the public link until a deployment account is intentionally configured and verified.
- Screenshots remain product evidence only; a hosted app does not prove data freshness or unlock blocked inputs.
- The app stays research-only: no investment advice, broker trading, order routing, auto-trading, direct buy/sell instructions, or fabricated data.

## Safe Hosting Boundary

Streamlit Community Cloud or a similar Python app host can run the public dashboard if it can install the `pyproject.toml` dependencies and launch the Streamlit entrypoint used by `make dashboard`.

Set the hosted app entrypoint to `dashboard.py`. The root `dashboard.py` file is a compatibility wrapper around `src.dashboard`, which keeps hosted platforms on a simple root-level Streamlit file while local operators keep using the source module directly. Keep `make dashboard` as the local verification path before and after deployment-specific changes.

Install dependencies from `requirements.txt` or `pyproject.toml`. The root `requirements.txt` contains only runtime app dependencies; optional research/provider extras and broker-style packages stay out of the hosted baseline unless intentionally configured.

Before sharing a hosted URL:

1. Confirm the app opens directly to public mode or clearly routes visitors there.
2. Keep provider keys, account identifiers, tokens, and broker/session files outside the repo.
3. Do not add secrets to committed files, screenshots, sample reports, or generated CSVs.
4. Do not claim FMP, Alpha Vantage, Finnhub, or broker-backed data is active unless the hosted environment actually has the secret configured and a reviewed one-ticker smoke has passed.
5. Do not claim complete coverage; readiness states must continue to show ready, partial, blocked, skipped, and excluded lanes.
6. Run the public gates again after any hosted-app-specific change.

## Secrets And Provider Keys

Local key setup belongs in ignored local files such as `config/provider_keys.env` or in the hosting platform's encrypted secrets UI. The repo should only contain templates and variable names.

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
make public-check
make browser-qa-evidence
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

If the hosted deployment changes app startup, route behavior, or copy, also review the five public pages:

Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History

Stop before publishing the hosted link if the first public view shows tracebacks, raw tables before the answer, command-heavy copy, missing research-only boundaries, or unavailable-provider claims.

## LinkedIn Link Rule

Use the GitHub repository link unless the hosted app exists, has been opened successfully, and has passed the same public-share boundaries. After a hosted app is verified, LinkedIn copy can say "hosted demo available"; until then, keep the wording as "GitHub portfolio/demo project with screenshots and local run instructions."
