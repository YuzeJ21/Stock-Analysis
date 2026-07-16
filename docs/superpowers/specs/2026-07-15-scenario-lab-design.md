# Scenario Lab Design

## Purpose

Scenario Lab answers: "How does the existing source-backed DCF change when I vary explicit assumptions?"

It is an assumption-testing surface inside the existing Single-Stock Report. It reuses the canonical valuation engine and never changes source rows, readiness, the Research Thesis Journal, or any report conclusion.

## Eligibility

Scenario Lab runs only when:

- the selected asset is an eligible operating company
- the selected profile marks the ticker DCF-ready
- the baseline DCF calculates a per-share result from source-backed inputs
- the scenario assumptions pass conservative bounds

Blocked inputs yield `blocked`; non-company assets yield `excluded`; invalid assumptions yield `invalid`. None of these states show valuation numbers.

## Contract

`ScenarioParameters` contains:

- revenue growth
- FCF margin
- WACC
- terminal growth
- forecast years

The lab keeps source-backed revenue, free cash flow, shares outstanding, cash, debt, and net debt immutable. A scenario cannot replace those facts.

Conservative bounds:

- revenue growth: -50% through 40%
- FCF margin: -50% through 45%
- WACC: 5% through 20%
- terminal growth: -2% through 5% and strictly below WACC
- forecast years: 1 through 10

The output preserves:

- selected profile and ticker
- deterministic input identity
- baseline and scenario assumptions
- exact changed assumptions
- baseline and scenario per-share scenario math
- scenario sensitivity range
- WACC/terminal-growth sensitivity grid
- terminal-value contribution
- source metadata and warnings

## UI

Scenario Lab sits inside the existing detailed Valuation tab. It does not add a page or appear before the selected-ticker readiness answer.

Controls use bounded sliders. The first answer states eligibility. Calculated output shows baseline scenario math, adjusted scenario math, a sensitivity range, terminal-value contribution, and changed assumptions. Source metadata and the full grid stay under Advanced.

The UI never shows upside/downside, target price, score, ranking, buy/sell/hold language, or portfolio sizing. It describes scenario math only.

## State And Persistence

Controls are Streamlit session state only. The lab does not write files. A future explicit export may create a generated artifact under `outputs`, but export is not part of this milestone.

## Verification

- blocked/excluded/invalid states fail closed
- source-backed baseline fields remain unchanged
- bounded assumption validation
- deterministic identity
- expected sensitivity directions
- terminal-value contribution
- dashboard controls only after readiness
- no transaction or action language
- full regression, dashboard, browser, public, pilot, and hygiene gates
