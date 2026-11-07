# LinkedIn Project Brief

## Featured Item

**Title**

`Stock Research Command Center | Interactive Company Research`

**Description**

`Explore a fictional company’s financial trends, peer valuation, and research notes. In Monitor, compare two saved observations and record why the follow-up is Reviewed or Still open. A separate AMD walkthrough uses a real SEC filing.`

**Primary link**

[Open the interactive English company research demo](https://yuzej21.github.io/Stock-Analysis/).

Use a current screenshot of the linked English demo for the Featured image. The [local Workbench screenshot](assets/linkedin-public-dashboard.png) can accompany a separate discussion of the full workspace. A screenshot shows the interface. Check readiness and source rights separately.

## What Visitors Can Review

### Two-minute external review path

1. Search for fictional `FICT` and open **Business Trend** in **Financial Trends**.
2. Compare eligible peers, open **Peer Read-Through**, and change the discount rate in the fictional **Scenario Lab**.
3. Open **Forward View**, **Catalysts**, and **Research Decision Lab** in **Research Notes**.
4. In **Monitor**, choose **Review saved evidence**. Compare the fixed `FICT-FY25-01` and `FICT-FY25-02` observations in **Saved evidence comparison**.
5. Return to Monitor and record **Reviewed** or **Still open** with a reason. The disposition and separate personal note reset on reload.

The secondary [AMD filing case](https://yuzej21.github.io/Stock-Analysis/amd.html) uses a dated real SEC 10-Q. It shows quarter drivers, a nine-month cash comparison, a sample follow-up, and why public peer valuation remains withheld. **Try the fictional evidence review** opens the synthetic Monitor with its fixed evidence pair.

GitHub-only review starts with the [README](../README.md) and its product map. Live dashboard review starts with `make dashboard` at `http://localhost:8501/`. The local Personal Research route is Research Desk -> Discover -> Company Workbench -> Monitor. The separately controlled Public route is Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History and opens with `make demo-dashboard` at `http://localhost:8501/?mode=public`.

## What the Full Workspace Adds

The local Python and Streamlit portfolio beta checks what evidence can be used now, keeps unsupported conclusions withheld, and lets a researcher revisit source-backed changes. Company Workbench groups business trend, valuation, forward context, uncertainty, and the next research task. Data Health and Proof History remain available for missing inputs and provenance.

For NEM, AMD, and DUK, the local Monitor can reopen an exact saved annual SEC observation pair and retain a reasoned **Reviewed** or **Still open** disposition in an ignored local file scoped to the issuer, ordered pair, and selected research profile. Saved evidence stays immutable. The fictional browser demo keeps its decision in page state until reload. See [Saved SEC company reviews](SEC_RESEARCH_REVIEWS.md).

The full Streamlit workspace runs locally. GitHub Pages hosts the fictional English demo and dated AMD case. A public full Streamlit deployment remains a separate gate in [Hosted Demo Deployment](HOSTED_DEMO_DEPLOYMENT.md).

## Now / Next / Not Yet

| Stage | Current answer | Boundary |
| --- | --- | --- |
| Now | Share the guided fictional Pages demo first, the dated AMD case second, and the local workspace through the repository. | These are controlled portfolio/demo examples. They do not prove current-market coverage or outside reviewer demand. |
| Next | Qualify a new issuer or period and make the evidence comparison clearer. | Distinguish an actual annual financial or filing change from a new retrieval or issuer-association metadata change. |
| Not yet | Host the full Streamlit workspace or claim broad fundamentals, peers, earnings, estimates, predictive validation, or commercial operation. | Each needs source rights, repeatable operations, and direct validation. |

The active sequence is in the [Roadmap](../ROADMAP.md). `make next-stage` prints the current package and source-proof decision ladder without changing local data. Run `make project-status-check` first and use `make provider-setup-checklist` when source-proof queues are exhausted. Do not run trusted-data pilot queues as a LinkedIn demo talking point unless project-status-check shows executable source-backed candidates.

## Suggested LinkedIn Post

I built Stock Research Command Center to make evidence gaps visible during company research. The [interactive English demo](https://yuzej21.github.io/Stock-Analysis/) follows a fictional company through financial trends, peer context, a valuation assumption, research notes, and a Monitor follow-up. You can compare two fixed observations and record why the follow-up is Reviewed or Still open. That decision resets on reload.

A [separate AMD case](https://yuzej21.github.io/Stock-Analysis/amd.html) uses a dated SEC filing and keeps unsupported public peer valuation withheld. The wider Python and Streamlit workspace runs locally. I built it as a research-only portfolio project.

## Share and Source Boundaries

- Screenshots are product evidence only. They are not data-freshness proof and do not establish source rights or complete coverage. `make readiness-ops-center` reports current selected-profile lane truth. `make status-check TOP_N=5` describes a saved generated snapshot that can be stale.
- Coverage boundary. Prices have broader local coverage, while fundamentals, share count, peer mapping, earnings, and analyst estimates can remain blocked or locked.
- Provider boundary. FMP, Alpha Vantage, and Finnhub are optional local fallbacks and are not configured by default. Provider setup alone does not establish a qualified source-backed lane.
- Share under the controlled portfolio/demo license. Do not describe the repository as open-source reuse or a commercial data product.
- The project does not provide investment advice, connect to a broker, route orders, auto-trade, or give direct buy or sell instructions. It is research-only.

## Demo Talking Points

- Begin with the linked English demo. Use the [Public Demo Walkthrough](PUBLIC_DEMO_WALKTHROUGH.md) for the short path.
- If asked about real evidence, open the dated AMD case and its SEC filing links. Do not present the fictional disposition as an AMD decision.
- If asked about the full product, explain the local Research Desk -> Discover -> Company Workbench -> Monitor path and the exact-pair NEM, AMD, and DUK review scope.
- Keep lane-level operator views, reviewed batch packets, provider setup, and validate / preview / apply guidance as follow-up context. The [Data Strategy](DATA_STRATEGY.md) and [Analysis Capability Audit](analysis_capability_audit.md) explain missing inputs and method limits.
- Historical picks, portfolio, ranking, and watchlist views are Operator-only compatibility utilities. They are not current Personal Research features.

Project repository [Stock Research Command Center](https://github.com/YuzeJ21/Stock-Analysis)
