# LinkedIn Project Brief

## Featured Item

**Title**

`Stock Research Command Center | Company Research, Valuation & Monitoring`

**Description**

`An evidence-first equity research workbench connecting company search, financial trends, peer comparisons, valuation scenarios, research notes and Monitor follow-ups. Save and replay evidence, inspect changes, and keep sources, periods, assumptions and gaps visible. This public example uses a real SEC filing; interactive tools are demonstrated separately with labelled synthetic data. The Python and Streamlit workspace runs locally. Research-only; no investment advice or trading automation.`

**Primary link**

[Open the real SEC filing example](https://yuzej21.github.io/Stock-Analysis/amd.html).

Use the [real SEC filing case screenshot](assets/amd-sec-filing-case.jpg) for the Featured image. It shows the dated, read-only public filing case. Check readiness and source rights separately.

The separate [interactive English company research demo](https://yuzej21.github.io/Stock-Analysis/) demonstrates the full guided workflow with labelled synthetic data. Use the [English company demo screenshot](assets/english-company-research-demo.png) when sharing that workflow separately.

## What Visitors Can Review

### Two-minute external review path

Follow **Company Search → Overview → Financial Trends → Valuation & Peers → Research Notes → Data Sources → Monitor**.

1. Search for fictional **FICT** or **Fogline Photonics** and open **Overview** for the business results, dated close, and peer result or gap.
2. In **Financial Trends**, compare annual and quarterly performance and open **Business Trend**.
3. In **Valuation & Peers**, switch between three and two eligible peers, inspect exclusions, open **Valuation methods** and **Peer Read-Through**, and change the discount rate in **Scenario Lab**.
4. In **Research Notes**, open **Forward View**, **Catalysts**, **Research Decision Lab**, and the **Research brief**, then add a follow-up.
5. Inspect **Data Sources** for periods, units, synthetic provenance, assumptions, and missing observations.
6. In **Monitor**, choose **Review saved evidence**. Compare the fixed `FICT-FY25-01` and `FICT-FY25-02` observations, then return and record **Reviewed** or **Still open** with a reason.

This static demo fetches no live data. The disposition, scenario changes, and personal note reset on reload.

The primary Featured [AMD filing case](https://yuzej21.github.io/Stock-Analysis/amd.html) uses the Q3 FY2026 SEC 10-Q filed November 4, 2026. It is a dated, read-only example showing quarter drivers, a nine-month cash comparison, a sample follow-up, and why public peer valuation remains withheld pending approved same-day price evidence. **Try the fictional evidence review** opens the synthetic Monitor with its fixed evidence pair; **Explore advanced research tools** opens the fictional Valuation & Peers section.

GitHub-only review starts with the [README](../README.md) and its product map. Live dashboard review starts with `make dashboard` at `http://localhost:8501/`. The local Personal Research route is Research Desk -> Discover -> Company Workbench -> Monitor. The separately controlled Public route is Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History and opens with `make demo-dashboard` at `http://localhost:8501/?mode=public`.

## What the Full Workspace Adds

The local Python and Streamlit portfolio beta checks what evidence can be used now, keeps unsupported conclusions withheld, and lets a researcher revisit source-backed changes. Company Workbench uses the same five sections: **Overview**, **Financial Trends**, **Valuation & Peers**, **Research Notes**, and **Data Sources**. It adds explicit source refresh, annual/quarterly metric charts and tables, separately qualified saved Business Trend, Scenario Lab and sensitivities, Peer Read-Through, Valuation Methods, and Historical Valuation Regime. Notes retain journal authoring, Decision Lab and outcome history, Forward View, catalysts, and the offline HTML Research Brief. Data Health and Proof History remain available for missing inputs and provenance. Online observations do not automatically qualify saved models; each tool retains its company, profile, source, and readiness requirements.

For NEM, AMD, and DUK, the local Monitor can reopen an exact saved annual SEC observation pair and retain a reasoned **Reviewed** or **Still open** disposition in an ignored local file scoped to the issuer, ordered pair, and selected research profile. Saved evidence stays immutable. The fictional browser demo keeps its decision in page state until reload. See [Saved SEC company reviews](SEC_RESEARCH_REVIEWS.md).

The full Streamlit workspace runs locally. GitHub Pages hosts the fictional English demo and dated AMD case. A public full Streamlit deployment remains a separate gate in [Hosted Demo Deployment](HOSTED_DEMO_DEPLOYMENT.md).

## Now / Next / Not Yet

| Stage | Current answer | Boundary |
| --- | --- | --- |
| Now | Share the dated SEC filing case as the Featured example, the guided fictional Pages demo for the full interactive workflow, and the local workspace through the repository. | These are controlled portfolio/demo examples. They do not prove current-market coverage or outside reviewer demand. |
| Next | Qualify exact native-currency filings for foreign issuers and demonstrate a meaningful subsequent filing change through Monitor. | Retain source dates, reporting periods, currency and security basis, and field-level gaps. |
| Not yet | Host the full Streamlit workspace or claim broad fundamentals, peers, earnings, estimates, predictive validation, or commercial operation. | Each needs source rights, repeatable operations, and direct validation. |

The active sequence is in the [Roadmap](../ROADMAP.md). `make next-stage` prints the current package and source-proof decision ladder without changing local data. Run `make project-status-check` first and use `make provider-setup-checklist` when source-proof queues are exhausted. Do not run trusted-data pilot queues as a LinkedIn demo talking point unless project-status-check shows executable source-backed candidates.

## Suggested LinkedIn Post

I built Stock Research Command Center to connect company performance, peer comparisons, valuation assumptions, sources, and research follow-ups in one workspace. The [public filing example](https://yuzej21.github.io/Stock-Analysis/amd.html) uses a dated SEC filing and keeps unsupported public peer valuation withheld. The wider Python and Streamlit workspace runs locally. I built it as a research-only portfolio project.

The separate [interactive English demo](https://yuzej21.github.io/Stock-Analysis/) illustrates the workflow with synthetic data. It includes business trends, Scenario Lab, Peer Read-Through, Forward View, catalysts, and a research brief. In Monitor, you can compare two fixed observations and record why a follow-up is Reviewed or Still open. The demo's notes and decisions reset on reload.

## Share and Source Boundaries

- Screenshots are product evidence only. They are not data-freshness proof and do not establish source rights or complete coverage. `make readiness-ops-center` reports current selected-profile lane truth. `make status-check TOP_N=5` describes a saved generated snapshot that can be stale.
- Coverage boundary. Prices have broader local coverage, while fundamentals, share count, peer mapping, earnings, and analyst estimates can remain blocked or locked.
- Provider boundary. FMP, Alpha Vantage, and Finnhub are optional local fallbacks and are not configured by default. Provider setup alone does not establish a qualified source-backed lane.
- Share under the controlled portfolio/demo license. Do not describe the repository as open-source reuse or a commercial data product.
- The project does not provide investment advice, connect to a broker, route orders, auto-trade, or give direct buy or sell instructions. It is research-only.

## Demo Talking Points

- Begin with the linked, dated SEC filing case and its filing sources. Its public peer valuation remains withheld; it does not show live prices or a real-company interactive workflow.
- For the full interactive workflow, open the separately labelled synthetic English demo. Use the [Public Demo Walkthrough](PUBLIC_DEMO_WALKTHROUGH.md) for the short path. Do not present the fictional disposition as an AMD decision.
- If asked about the full product, explain the local Research Desk -> Discover -> Company Workbench -> Monitor path and the exact-pair NEM, AMD, and DUK review scope.
- Keep lane-level operator views, reviewed batch packets, provider setup, and validate / preview / apply guidance as follow-up context. The [Data Strategy](DATA_STRATEGY.md) and [Analysis Capability Audit](analysis_capability_audit.md) explain missing inputs and method limits.
- Historical picks, portfolio, ranking, and watchlist views are Operator-only compatibility utilities. They are not current Personal Research features.

Project repository [Stock Research Command Center](https://github.com/YuzeJ21/Stock-Analysis)
