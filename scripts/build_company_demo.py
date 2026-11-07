"""Build an offline, English-language company research demo from synthetic data."""

import argparse
from base64 import b64encode
from hashlib import sha256
from html import escape
from pathlib import Path
from statistics import median


_TITLE = "Stock Research Command Center | Guided Demo"
_DESCRIPTION = "Research a fictional company, review business trends and peers, test valuation assumptions, and track a follow-up."
_COMPANY = "Fogline Photonics"
_TICKER = "FICT"
_CLOSE_DATE = "Oct 30, 2026"
_PRIOR_CLOSE_DATE = "Oct 29, 2026"
_CLOSE = 48.0
_SAMPLE_FILING_DATE = "Feb 12, 2026"
_FOLLOW_UP = "Check whether revenue growth and operating income remain aligned in the next annual filing."
_ANNUAL = (
    (2023, 78, 6, 0.95),
    (2024, 96, 11, 1.60),
    (2025, 120, 17, 2.00),
)
_QUARTERLY = (
    ("Q1 FY2025", 26, 22, 3.4),
    ("Q2 FY2025", 29, 24, 4.2),
    ("Q3 FY2025", 31, 24, 4.4),
    ("Q4 FY2025", 34, 26, 5.0),
)
_PEERS = (
    ("Peer A", 36.0, 2.0),
    ("Peer B", 40.0, 2.0),
    ("Peer C", 44.0, 2.0),
    ("Peer D", 30.0, -0.5),
)
_STEPS = (
    ("overview", "Overview"),
    ("financials", "Financial Trends"),
    ("valuation", "Valuation &amp; Peers"),
    ("notes", "Research Notes"),
    ("sources", "Data Sources"),
)
_SCRIPT_PATH = Path(__file__).with_name("company_demo_interactions.js")
_STYLE = """
:root {
  color-scheme: light; --ink: #152b24; --muted: #496056; --line: #d3e0d7;
  --pine: #144c3d; --mint: #e8f3ed; --paper: #fff; --ground: #f4f7f3;
  --amber: #775112; --amber-bg: #f9f1dd;
  font: 1rem/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body { margin: 0; color: var(--ink); background: var(--ground); }
a { color: var(--pine); text-underline-offset: .18em; }
:focus-visible { outline: 3px solid #196853; outline-offset: 4px; }
button, input, textarea { font: inherit; color: inherit; }
button { cursor: pointer; }
p, figure { margin: 0; }
h1, h2, h3, h4 { margin: 0; line-height: 1.16; }
h1 { font-size: clamp(1rem, 2.5vw, 1.23rem); letter-spacing: -.02em; }
h2 { font-size: clamp(2rem, 5vw, 3.35rem); letter-spacing: -.05em; overflow-wrap: anywhere; }
h3 { font-size: 1.25rem; letter-spacing: -.025em; }
.skip-link { position: absolute; z-index: 2; top: 0; left: 1rem; padding: .6rem 1rem;
  background: var(--paper); transform: translateY(-120%); }
.skip-link:focus { transform: translateY(.5rem); }
.masthead { border-bottom: 1px solid var(--line); background: var(--paper); }
.masthead-inner, .layout, .page-footer { max-width: 79rem; margin-inline: auto;
  padding-inline: clamp(1rem, 4vw, 2.75rem); }
.masthead-inner { min-height: 5.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.brand { display: flex; gap: .8rem; align-items: center; }
.brand-mark { flex: none; display: grid; place-items: center; width: 2.4rem; height: 2.4rem;
  border-radius: .65rem; color: #fff; background: var(--pine); font-size: .75rem; font-weight: 800; letter-spacing: .06em; }
.eyebrow { color: var(--pine); font-weight: 750; font-size: .76rem; letter-spacing: .1em; text-transform: uppercase; }
.badge { display: inline-flex; width: fit-content; align-items: center; border-radius: 999px; padding: .26rem .64rem;
  color: var(--pine); background: var(--mint); font-size: .8rem; font-weight: 750; line-height: 1.35; }
.badge--warning { color: var(--amber); background: var(--amber-bg); }
.layout { display: grid; grid-template-columns: minmax(10.75rem, .23fr) minmax(0, 1fr);
  gap: clamp(1.4rem, 4vw, 3rem); padding-block: clamp(1.4rem, 4vw, 3rem); }
.steps { position: sticky; top: 1.5rem; align-self: start; }
.workspace-rail { position: sticky; top: 1.5rem; align-self: start; display: grid; gap: 1.4rem; }
.workspace-rail .steps { position: static; }
.workflow-links { list-style: none; margin: 0; padding: 0; display: grid; gap: .3rem; }
.company-heading { display: grid; gap: .45rem; margin-bottom: 1rem; }
.company-heading p:last-child { color: var(--muted); }
.company-heading h2 { font-size: clamp(2rem, 5vw, 2.8rem); }
.company-section-title { font-size: clamp(1.5rem, 4vw, 1.9rem); letter-spacing: -.035em; }
.panel-intro--compact .company-section-title { font-size: 1.1rem; letter-spacing: -.02em; }
.table-scroll { min-width: 0; overflow-x: auto; }
.table-scroll table { min-width: 26rem; }
.analysis-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
.analysis-grid .surface { display: grid; align-content: start; gap: .55rem; }
.steps-title { margin: 0 0 .65rem .55rem; }
.steps ol { list-style: none; padding: 0; margin: 0; display: grid; gap: .3rem; }
.steps a { display: flex; min-height: 2.9rem; align-items: center; gap: .65rem; padding: .4rem .55rem;
  border: 1px solid transparent; border-radius: .62rem; color: var(--ink); font-size: .91rem; text-decoration: none; font-weight: 650; }
.steps a:hover, .steps a[aria-current] { color: var(--pine); background: var(--mint); border-color: #bbd6c7; }
.step-number { display: grid; flex: none; place-items: center; width: 1.55rem; height: 1.55rem;
  color: var(--pine); background: var(--paper); border: 1px solid #c5d9cd; border-radius: 50%; font-size: .74rem; font-weight: 800; }
.scope-note { margin-top: 1.2rem; padding: .75rem .6rem; border-top: 1px solid var(--line);
  color: var(--muted); font-size: .8rem; }
main, .panel { min-width: 0; }
.panel { display: grid; align-content: start; gap: 1.25rem; scroll-margin-top: 1rem; }
.panel + .panel { margin-top: 2rem; }
.panel[hidden] + .panel { margin-top: 0; }
.panel-intro { display: grid; gap: .5rem; }
.panel-intro p:last-child { color: var(--muted); max-width: 60ch; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) minmax(14rem, .55fr); gap: clamp(1rem, 4vw, 2.2rem);
  padding: clamp(1.2rem, 4vw, 2.4rem); background: var(--paper); border: 1px solid var(--line);
  border-top: .3rem solid #28634f; border-radius: 1rem; }
.hero-content, .case-file, .note-box { min-width: 0; display: grid; align-content: start; gap: .85rem; }
.hero-content .panel-intro { margin-bottom: .35rem; }
.case-file { align-self: stretch; padding: 1.15rem; color: #f2f9f5;
  background: #163f34; border-radius: .8rem; }
.case-file .eyebrow { color: #c3e6d2; }
.case-file p:not(.eyebrow) { color: #e0eee6; font-size: .9rem; }
.case-file ul { margin: .2rem 0 0; padding: 0; list-style: none; }
.case-file li { padding: .52rem 0; border-top: 1px solid #527b6d; font-size: .87rem; }
.case-file a { color: #e0eee6; font-weight: 750; }
.search-form, .note-form { display: grid; gap: .5rem; }
.field-label { font-weight: 750; font-size: .9rem; }
.form-row, .actions { display: flex; flex-wrap: wrap; gap: .65rem; align-items: center; }
.form-row input { flex: 1 1 10rem; min-width: 0; }
input[type="search"], textarea { min-height: 2.85rem; border: 1px solid #789687; border-radius: .48rem;
  padding: .6rem .75rem; background: var(--paper); }
textarea { width: 100%; resize: vertical; }
.button { display: inline-flex; align-items: center; justify-content: center; width: fit-content; min-height: 2.8rem;
  padding: .55rem .85rem; border: 1px solid var(--pine); border-radius: .48rem; background: var(--pine);
  color: #fff; text-decoration: none; font-weight: 750; font-size: .9rem; }
.button:hover { background: #103c31; }
.button--secondary { color: var(--pine); background: var(--paper); border-color: #789687; }
.button--secondary:hover { background: var(--mint); }
.helper, .status, .metric-context, .source-note { color: var(--muted); font-size: .87rem; }
.status:not(:empty) { padding: .35rem 0; }
.result, .surface { min-width: 0; padding: clamp(.9rem, 2.8vw, 1.35rem); background: var(--paper);
  border: 1px solid var(--line); border-radius: .75rem; }
.result { display: grid; gap: .45rem; background: var(--mint); }
.result .button { margin-top: .3rem; }
.metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(0, 1.45fr); gap: .75rem; }
.metric { min-width: 0; display: grid; align-content: start; gap: .2rem; padding: 1rem;
  border: 1px solid var(--line); border-radius: .65rem; background: var(--paper); }
.metric-label { font-size: .84rem; color: var(--muted); font-weight: 700; }
.metric-value { font-size: clamp(1.2rem, 3vw, 1.7rem); font-weight: 780; letter-spacing: -.035em; }
.peer-callout { background: var(--mint); border-color: #bbd6c7; }
.peer-callout-title { color: var(--pine); font-size: .84rem; letter-spacing: normal; line-height: 1.55; }
.peer-callout-answer { font-weight: 780; font-size: 1.16rem; line-height: 1.35; }
.peer-callout-link { display: inline-flex; width: fit-content; align-items: center; min-height: 2.75rem;
  font-size: .88rem; font-weight: 750; }
.trend-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .9fr); gap: .8rem; }
.chart svg { width: 100%; height: auto; display: block; margin-top: .7rem; }
.chart text { font: 12px system-ui, sans-serif; fill: var(--muted); }
.chart .chart-value { fill: var(--ink); font-weight: 750; }
.chart .chart-bar { fill: #80b29b; }
.chart .chart-bar:last-of-type { fill: #28634f; }
.chart-line { stroke: #bbcfc4; stroke-width: 1; }
.chart figcaption { margin-top: .25rem; color: var(--muted); font-size: .82rem; }
table { width: 100%; border-collapse: collapse; margin-top: .6rem; font-size: .88rem; }
caption { text-align: left; margin-bottom: .45rem; color: var(--muted); font-size: .82rem; }
th, td { padding: .62rem .45rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { font-size: .78rem; color: var(--muted); }
tbody th { color: var(--ink); }
.numbers :is(th,td):not(:first-child) { text-align: right; }
details { background: var(--paper); border: 1px solid var(--line); border-radius: .55rem; padding-inline: .9rem; }
summary { min-height: 2.8rem; padding-block: .62rem; font-weight: 750; color: var(--pine); cursor: pointer; }
details[open] { padding-bottom: .8rem; }
details ul { margin: .45rem 0 0; padding-inline-start: 1.15rem; }
details li + li { margin-top: .3rem; }
.peer-controls { border: 0; margin: 0; padding: 0; min-width: 0; }
.peer-controls legend { font-size: .9rem; font-weight: 750; margin-bottom: .4rem; }
.peer-controls label { display: inline-flex; align-items: center; gap: .45rem; min-height: 2.85rem; padding: .3rem .65rem;
  margin: 0 .4rem .25rem 0; border: 1px solid #789687; border-radius: .48rem; background: var(--paper); cursor: pointer; }
.peer-controls label:has(input:checked) { background: var(--mint); border-color: var(--pine); color: var(--pine); font-weight: 750; }
.peer-controls input { accent-color: var(--pine); }
.peer-result { display: grid; gap: .55rem; padding: 1rem; border-left: .27rem solid #28634f; }
.peer-result--withheld { border-left-color: #ac7a23; }
.demo-state--withheld { display: none; }
body:has(#demo-withheld:checked) .demo-state--available { display: none; }
body:has(#demo-withheld:checked) .demo-state--withheld { display: block; }
.peer-evidence { margin-top: .15rem; }
.tool-grid, .tool-list, .tool-body { display: grid; gap: .65rem; }
.tool-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; }
.tool-grid details { min-width: 0; }
.tool-body > table, .tool-body > ul { margin-top: 0; }
.tool-body > p, .decision-lanes dd { font-size: .9rem; }
.business-trend-table :is(th,td) { padding-inline: .3rem; }
.decision-lanes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .45rem 1rem; margin: 0; }
.decision-lanes dt { color: var(--pine); font-size: .84rem; font-weight: 750; }
.decision-lanes dd { margin: 0; }
.scenario-values { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .45rem; }
.scenario-values > div { min-width: 0; border-radius: .45rem; padding: .48rem .6rem; background: var(--mint); }
.scenario-values strong, .scenario-values output { display: block; font-size: 1.12rem; font-weight: 780; }
.scenario-control input { display: block; width: 100%; min-height: 2.75rem; margin: 0; accent-color: var(--pine); }
.tool-body > .scenario-assumptions { font-size: .8rem; }
.note-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .65fr); gap: .85rem; }
.note-box ul { margin: 0; padding-left: 1.2rem; }
.monitor-note { display: grid; gap: .65rem; border-left: .27rem solid #28634f; }
.monitor-note-text { white-space: pre-wrap; overflow-wrap: anywhere; }
.saved-evidence { scroll-margin-top: 1rem; }
.evidence-observations { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
.evidence-observations article { min-width: 0; display: grid; gap: .3rem; padding: .75rem;
  border: 1px solid var(--line); border-radius: .48rem; }
.evidence-observations h4 { overflow-wrap: anywhere; }
.review-choices { border: 0; margin: 0; padding: 0; }
.review-choices label { display: inline-flex; gap: .35rem; align-items: center; min-height: 2.75rem; }
.review-choices input { accent-color: var(--pine); }
.page-footer { padding-block: 1rem 1.5rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .82rem; }
@media (max-width: 1000px) {
  .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .peer-callout { grid-column: 1 / -1; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: .8rem; }
}
@media (max-width: 800px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  .steps, .workspace-rail { position: static; }
  .workspace-rail { gap: .6rem; }
  .workflow-links { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .steps-title, .scope-note { display: none; }
  .steps ol { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .35rem; }
  .steps a { padding-inline: .45rem; font-size: .82rem; gap: .35rem; border-color: var(--line); background: var(--paper); }
  .step-number { width: 1.3rem; height: 1.3rem; font-size: .7rem; }
}
@media (max-width: 600px) {
  .masthead-inner { align-items: flex-start; flex-direction: column; justify-content: center; gap: .45rem; padding-block: .8rem; }
  .layout { padding-top: .8rem; gap: 1rem; }
  .steps ol { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .hero, .trend-grid, .note-grid, .tool-grid, .decision-lanes, .evidence-observations, .analysis-grid { grid-template-columns: minmax(0, 1fr); }
  .metrics { gap: .45rem; }
  .metric { padding: .6rem; }
  .metric-value { font-size: 1.12rem; }
  .metric-context { font-size: .77rem; }
  .peer-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
  .peer-table tr { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .15rem; padding: .6rem 0; border-bottom: 1px solid var(--line); }
  .peer-table :is(th,td) { padding: .24rem; border: 0; }
  .peer-table td::before { display: block; content: attr(data-label); color: var(--muted); font-size: .72rem; font-weight: 750; }
  .peer-table tbody th, .peer-table td:last-child { grid-column: 1 / -1; }
}
@media (max-width: 330px) {
  .metrics { grid-template-columns: minmax(0, 1fr); }
}
@media (forced-colors: active) {
  :focus-visible { outline-color: Highlight; }
}
"""


def _step_link(step, label, *, button=True):
    button_class = ' class="button"' if button else ""
    return f'<a{button_class} href="#{step}" data-demo-go="{step}">{label}</a>'


def _panel(step, eyebrow, title, intro, content, *, compact=False):
    eyebrow_html = "" if compact else f'<p class="eyebrow">{eyebrow}</p>'
    intro_html = "" if compact else f"<p>{intro}</p>"
    return f"""<section class="panel" id="{step}" data-demo-page="{step}" data-demo-panel
  aria-labelledby="{step}-title" tabindex="-1">
  <header class="panel-intro{' panel-intro--compact' if compact else ''}">
    {eyebrow_html}
    <h2 class="company-section-title" id="{step}-title" data-demo-title tabindex="-1">{title}</h2>
    {intro_html}
  </header>
  {content}
</section>"""


def _discover():
    return f"""<section class="panel" id="discover" data-demo-page="discover" data-demo-panel
  aria-labelledby="discover-title" tabindex="-1">
  <div class="hero">
    <div class="hero-content">
      <header class="panel-intro">
        <p class="eyebrow">Company Search</p>
        <h2 id="discover-title" data-demo-title tabindex="-1">Find a company</h2>
        <p>Start with one company and follow the evidence from its reported results to a research follow-up.</p>
      </header>
      <form class="search-form" id="demo-search-form" data-demo-search data-demo-company-name="{_COMPANY}" data-demo-company-ticker="{_TICKER}">
        <label class="field-label" for="demo-search-input">Company name or ticker</label>
        <div class="form-row">
          <input id="demo-search-input" data-demo-query type="search" maxlength="80"
            autocomplete="off" placeholder="e.g. {_COMPANY}" aria-describedby="demo-search-hint">
          <button class="button" type="submit">Search</button>
          <button class="button button--secondary" type="reset">Clear</button>
        </div>
        <p class="helper" id="demo-search-hint">Try {_COMPANY} or {_TICKER}.</p>
        <p class="status" id="demo-search-status" data-demo-search-status role="status"></p>
      </form>
      <div class="result" id="demo-search-result" data-demo-result hidden>
        <span class="badge">{_TICKER} · Fictional company</span>
        <h3>{_COMPANY}</h3>
        <p>Photonics and optical components</p>
        {_step_link("overview", "Open Company Workbench")}
      </div>
      <noscript><p class="helper">Use the company section links to review the sample without interactive search.</p></noscript>
    </div>
    <aside class="case-file" aria-label="Included company case">
      <p class="eyebrow">Included case · {_TICKER}</p>
      <h3>{_COMPANY}</h3>
      <p>Follow a fictional optical components company through the full research flow.</p>
      <ul>
        <li>Three sample fiscal years</li>
        <li>One dated close and four peer candidates</li>
        <li>One follow-up to carry into Monitor</li>
      </ul>
      <p><a href="./amd.html">Explore the real AMD filing case</a></p>
    </aside>
  </div>
</section>"""


def _revenue_chart():
    bars = []
    peak_revenue = max(row[1] for row in _ANNUAL)
    for index, (year, revenue, _, _) in enumerate(_ANNUAL):
        x = 34 + index * 104
        height = revenue * 140 / peak_revenue
        y = 172 - height
        bars.append(f'<rect class="chart-bar" x="{x}" y="{y:g}" width="58" height="{height:g}" rx="5"/>'
                    f'<text class="chart-value" x="{x+29}" y="{y-8:g}" text-anchor="middle">{revenue}M</text>'
                    f'<text x="{x+29}" y="193" text-anchor="middle">FY {year}</text>')
    description = ", ".join(f"fiscal {year}: {revenue} million dollars" for year, revenue, _, _ in _ANNUAL)
    return f"""<figure class="surface chart">
  <h3>Annual revenue</h3>
  <svg viewBox="0 0 330 200" role="img" aria-labelledby="revenue-title revenue-desc">
    <title id="revenue-title">Reported annual revenue</title>
    <desc id="revenue-desc">{description}.</desc>
    <path class="chart-line" d="M18 172H314"/>
    {''.join(bars)}
  </svg>
  <figcaption>Fiscal years ended December 31. USD millions.</figcaption>
</figure>"""


def _business_trend():
    rows = "".join(
        f'<tr><th scope="row">{quarter}</th><td>{revenue}M</td><td>{prior}M</td>'
        f'<td>{(revenue / prior - 1) * 100:+.1f}%</td><td>{income / revenue:.1%}</td></tr>'
        for quarter, revenue, prior, income in _QUARTERLY
    )
    return f"""<details>
    <summary>Business Trend</summary>
    <div class="tool-body">
      <p>Revenue growth accelerated into the second half of FY2025. Compare the same quarters a year earlier
        and check whether operating margin improved through the year.</p>
      <table class="numbers business-trend-table">
        <caption>Fictional quarterly statements · USD revenue · margin for FY2025</caption>
        <thead><tr><th scope="col">Quarter</th><th scope="col">Revenue</th><th scope="col">Prior year</th><th scope="col">YoY</th>
          <th scope="col">Op. margin</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </details>"""


def _overview(peer_summary):
    year, revenue, _, eps = _ANNUAL[-1]
    _, prior_revenue, _, _ = _ANNUAL[-2]
    revenue_change = (revenue / prior_revenue - 1) * 100
    rows = "".join(f'<tr><th scope="row">{fy}</th><td>{sales}M</td><td>{income}M</td><td>{earnings:.2f}</td></tr>'
                   for fy, sales, income, earnings in _ANNUAL)
    content = f"""<div class="metrics" aria-label="Company snapshot">
    <article class="metric" data-company-answer="price">
      <p class="metric-label">Dated close</p><p class="metric-value">USD {_CLOSE:.2f}</p><p class="metric-context">{_CLOSE_DATE}</p>
    </article>
    <article class="metric" data-company-answer="financial">
      <p class="metric-label">Annual revenue</p><p class="metric-value">USD {revenue}M</p>
      <p class="metric-context">FY {year} · up {revenue_change:g}% year over year</p>
    </article>
    <article class="metric">
      <p class="metric-label">Annual diluted EPS</p><p class="metric-value">USD {eps:.2f}</p><p class="metric-context">FY {year} · reported</p>
    </article>
    <article class="metric peer-callout" data-demo-peer-callout aria-labelledby="peer-callout-title">
      <div>
        <h3 id="peer-callout-title" class="peer-callout-title">Peer valuation</h3>
        {peer_summary}
      </div>
      <a class="peer-callout-link" href="#valuation" data-demo-go="valuation" data-demo-peer-evidence>View why</a>
    </article>
  </div>
  <div class="trend-grid">
    {_revenue_chart()}
    <div class="surface">
      <h3>Reported financials</h3>
      <table class="numbers">
        <caption>Fictional annual statements · USD</caption>
        <thead><tr><th scope="col">FY</th><th scope="col">Revenue</th><th scope="col">Operating income</th><th scope="col">Diluted EPS</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
  <details>
    <summary>View financial and price evidence</summary>
    <ul>
      <li>Fictional FY {year} statement, year ended Dec 31, {year}, dated {_SAMPLE_FILING_DATE}.
        Revenue USD {revenue}M, diluted EPS USD {eps:.2f}.</li>
      <li>FY {year - 1} revenue USD {prior_revenue}M, same reporting currency and year-end. Change = {revenue}M ÷ {prior_revenue}M − 1.</li>
      <li>Sample daily price record dated {_CLOSE_DATE}: closing price USD {_CLOSE:.2f}.</li>
    </ul>
  </details>
  <div class="actions">{_step_link("financials", "Explore Financial Trends")}
    {_step_link("sources", "View Data Sources", button=False)}</div>"""
    return _panel("overview", "Company snapshot", "Overview",
                  "The reported business, dated close, and peer result in one view.", content, compact=True)


def _financials():
    annual_rows = "".join(
        f'<tr><th scope="row">{year}</th><td>{income / revenue:.1%}</td>'
        f'<td>{(revenue / _ANNUAL[index - 1][1] - 1):+.1%}</td>'
        f'<td>{(income / _ANNUAL[index - 1][2] - 1):+.1%}</td></tr>'
        if index else f'<tr><th scope="row">{year}</th><td>{income / revenue:.1%}</td><td>—</td><td>—</td></tr>'
        for index, (year, revenue, income, _) in enumerate(_ANNUAL)
    )
    bars = []
    for index, (quarter, revenue, _, income) in enumerate(_QUARTERLY):
        margin = income / revenue * 100
        x = 31 + index * 92
        height = margin * 7
        y = 141 - height
        bars.append(f'<rect class="chart-bar" x="{x}" y="{y:g}" width="52" height="{height:g}" rx="5"/>'
                    f'<text class="chart-value" x="{x + 26}" y="{y - 7:g}" text-anchor="middle">{margin:.1f}%</text>'
                    f'<text x="{x + 26}" y="161" text-anchor="middle">{quarter}</text>')
    description = ", ".join(f"{quarter}: {income / revenue:.1%}" for quarter, revenue, _, income in _QUARTERLY)
    content = f"""<div class="trend-grid">
    <figure class="surface chart">
      <h3>Quarterly operating margin</h3>
      <svg viewBox="0 0 390 175" role="img" aria-labelledby="margin-title margin-desc">
        <title id="margin-title">Fictional quarterly operating margin</title><desc id="margin-desc">{description}.</desc>
        <path class="chart-line" d="M16 141H374"/>{''.join(bars)}
      </svg>
      <figcaption>FY2025 standalone quarters. Operating income ÷ revenue.</figcaption>
    </figure>
    <section class="surface" aria-labelledby="annual-performance-title">
      <h3 id="annual-performance-title">Annual operating performance</h3>
      <div class="table-scroll"><table class="numbers">
        <caption>Fictional annual statements · year ended December 31</caption>
        <thead><tr><th scope="col">FY</th><th scope="col">Op. margin</th><th scope="col">Revenue YoY</th>
          <th scope="col">Op. income YoY</th></tr></thead><tbody>{annual_rows}</tbody>
      </table></div>
      <p class="source-note">No FY2022 comparison is included; FY2023 growth is unavailable.</p>
    </section>
  </div>
  {_business_trend()}
  <div class="analysis-grid">
    <section class="surface" aria-labelledby="operating-analysis-title">
      <h3 id="operating-analysis-title">What changed in the business</h3>
      <p>FY2025 revenue rose 25.0%, while operating income rose 54.5%. Operating margin improved
        from 11.5% to 14.2%. The sample supports improving operating profitability.</p>
      <p class="source-note">Segment mix, customer concentration, and expense drivers are not included.
        These observations do not establish why profitability improved.</p>
    </section>
    <section class="surface" aria-labelledby="cash-flow-title">
      <h3 id="cash-flow-title">Cash flow</h3>
      <span class="badge badge--warning">Evidence gap</span>
      <p>Reported cash flow is unavailable in this fictional statement set. Operating income is not cash flow.</p>
      <p class="source-note">The Scenario Lab's 10% cash-flow margin is an assumption. It does not establish
        reported operating cash flow, capital expenditure, or free cash flow.</p>
      <p>{_step_link("valuation", "Open Scenario Lab and valuation tools", button=False)}</p>
    </section>
  </div>
  <div class="actions">{_step_link("valuation", "Explore Valuation &amp; Peers")}
    {_step_link("sources", "View financial sources", button=False)}</div>"""
    return _panel("financials", "Business performance", "Financial Trends",
                  "Compare matching annual and quarterly periods, then separate operating performance from cash generation.", content)


def _peer_scenario(withheld):
    company_eps = _ANNUAL[-1][3]
    company_pe = _CLOSE / company_eps
    rows, eligible_multiples = [], []
    for name, price, eps in _PEERS:
        close_date = _PRIOR_CLOSE_DATE if withheld and name == "Peer C" else _CLOSE_DATE
        if eps <= 0:
            multiple, eligibility = "—", "Excluded · non-positive EPS"
        elif close_date != _CLOSE_DATE:
            multiple, eligibility = "—", "Excluded · different close date"
        else:
            eligible_multiples.append(price / eps)
            multiple, eligibility = f"{price / eps:.1f}×", "Eligible"
        rows.append(f"""<tr><th scope="row">{name}</th>
          <td data-label="Close date">{close_date}</td><td data-label="Close">{price:.2f}</td>
          <td data-label="Annual diluted EPS">{eps:.2f}</td><td data-label="Annual P/E">{multiple}</td>
          <td data-label="Eligibility">{eligibility}</td></tr>""")
    count = len(eligible_multiples)
    multiple_summary = f"{company_pe:.1f}× annual P/E"
    if count < 3:
        badge = f'<span class="badge badge--warning">{count} eligible peers · 3 required</span>'
        answer = "Peer comparison withheld"
        short_answer = answer
        context = f"Company P/E {company_pe:.1f}×. A third eligible same-day reference is required."
        extra_evidence = f"<li>Peer C closed on {_PRIOR_CLOSE_DATE}. It is outside the {_CLOSE_DATE} comparison.</li>"
    else:
        peer_median = median(eligible_multiples)
        relative_pct = (company_pe / peer_median - 1) * 100
        badge = f'<span class="badge">{count} eligible peers · comparison available</span>'
        direction = "above" if relative_pct > 0 else "below"
        answer = (f"Annual P/E is {abs(relative_pct):.1f}% {direction} the peer median"
                  if relative_pct else "Annual P/E matches the peer median")
        short_answer = (f"{abs(relative_pct):.1f}% {direction} peers"
                        if relative_pct else "In line with peers")
        multiple_summary += f" · {peer_median:.1f}× peer median"
        context = f"Company P/E {company_pe:.1f}× · Peer median {peer_median:.1f}× · {_CLOSE_DATE} closes."
        extra_evidence = f"<li>Relative difference = {company_pe:.1f}× ÷ {peer_median:.1f}× − 1.</li>"
    state = "withheld" if withheld else "available"
    summary = f"""<div class="demo-state--{state}">
      <p class="peer-callout-answer">{short_answer}</p>
      <p class="metric-context">{multiple_summary}</p>
      <p class="metric-context">{count} eligible · {len(_PEERS) - count} excluded</p>
    </div>"""
    comparison = f"""<div class="demo-state--{state}">
    <article class="surface peer-result{' peer-result--withheld' if withheld else ''}" data-company-answer="valuation">
      {badge}<h3>{answer}</h3><p>{context}</p>
      <details class="peer-evidence">
        <summary>View peer evidence</summary>
        <ul>
          <li>Company P/E = USD {_CLOSE:.2f} closing price ÷ USD {company_eps:.2f} reported annual diluted EPS.</li>
          <li>The sample requires same-day closes, positive annual diluted EPS, and fiscal-year start and end dates within 35 days of the company’s.</li>
          {extra_evidence}
          <li>Peer D is excluded because its annual diluted EPS is negative.</li>
          <li>Evidence: the sample close records and annual statement fields in the peer table.</li>
        </ul>
      </details>
    </article>
  </div>"""
    table = f"""<div class="demo-state--{state}">
    <div class="surface">
      <h3>Peer candidates</h3>
      <table class="peer-table">
        <caption>Fictional source records · FY 2025 ended Dec 31 · USD</caption>
        <thead><tr><th scope="col">Peer</th><th scope="col">Close date</th><th scope="col">Close</th>
          <th scope="col">Annual diluted EPS</th><th scope="col">Annual P/E</th><th scope="col">Eligibility</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
  </div>"""
    return summary, comparison, table


def _scenario_lab():
    baseline_rate, growth, terminal, years = 9, 0.08, 0.03, 5
    margin = 0.10
    cash_flows = [_ANNUAL[-1][1] * margin * (1 + growth) ** year for year in range(1, years + 1)]
    rates = range(7, 15)
    values = []
    for rate in rates:
        discount = rate / 100
        terminal_value = cash_flows[-1] * (1 + terminal) / (discount - terminal)
        value = sum(cash / (1 + discount) ** year for year, cash in enumerate(cash_flows, start=1))
        values.append(f"USD {value + terminal_value / (1 + discount) ** years:.1f}M")
    baseline = values[baseline_rate - rates.start]
    sensitivity_rows = "".join(f'<tr><th scope="row">{rate}%</th><td>{value}</td></tr>'
                               for rate, value in zip(rates, values))
    return f"""<details data-demo-scenario-values="{','.join(values)}">
    <summary>Scenario Lab</summary>
    <div class="tool-body">
      <p>See how WACC affects the value of the same fictional cash flows.</p>
      <div class="scenario-values" role="group" aria-label="Illustrative DCF values">
        <div><p class="metric-label">Baseline at {baseline_rate}% WACC</p>
          <strong data-demo-scenario-baseline>{baseline}</strong></div>
        <div><p class="metric-label">Scenario</p>
          <output for="demo-scenario-wacc" data-demo-scenario-value>{baseline}</output></div>
      </div>
      <div class="scenario-control" data-demo-scenario-control hidden>
        <label class="field-label" for="demo-scenario-wacc">Scenario WACC</label>
        <span class="helper" data-demo-scenario-rate aria-hidden="true">{baseline_rate}%</span>
        <input id="demo-scenario-wacc" type="range" min="{rates.start}" max="{rates.stop - 1}" step="1"
          value="{baseline_rate}" aria-valuetext="{baseline_rate}%" aria-describedby="demo-scenario-assumptions">
      </div>
      <p class="source-note" data-demo-scenario-static>This view shows the baseline at {baseline_rate}% WACC.
        The interactive slider requires scripts.</p>
      <p class="source-note scenario-assumptions" id="demo-scenario-assumptions">Fictional DCF · {years} years ·
        {growth:.0%} annual growth · {margin:.0%} cash-flow margin · {terminal:.0%} terminal growth ·
        USD model values.</p>
    </div>
  </details>
  <details>
    <summary>Sensitivity analysis</summary>
    <div class="tool-body">
      <p>Hold growth, cash-flow margin, terminal growth, and forecast length constant. Only WACC changes.</p>
      <table class="numbers"><caption>Same fictional DCF assumptions as Scenario Lab</caption>
        <thead><tr><th scope="col">WACC</th><th scope="col">Model value</th></tr></thead>
        <tbody>{sensitivity_rows}</tbody>
      </table>
      <p class="source-note">Model values are not a reported metric or a per-share price target.</p>
    </div>
  </details>"""


def _valuation(comparisons, tables):
    content = f"""<fieldset class="peer-controls">
    <legend>Change the peer evidence</legend>
    <label><input type="radio" id="demo-available" name="demo-scenario" checked> 3 eligible peers</label>
    <label><input type="radio" id="demo-withheld" name="demo-scenario"> 2 eligible peers</label>
  </fieldset>
  {comparisons}
  <div class="tool-grid" role="group" aria-label="Valuation research tools">
    <details>
      <summary>Valuation methods</summary>
      <div class="tool-body">
        <p><strong>Annual diluted P/E.</strong> USD {_CLOSE:.2f} close ÷ USD {_ANNUAL[-1][3]:.2f} FY2025 diluted EPS =
          {_CLOSE / _ANNUAL[-1][3]:.1f}×. The peer result requires at least three qualifying same-day references.</p>
        <p><strong>Illustrative DCF.</strong> Scenario Lab uses explicit growth, cash-flow margin, and discount-rate
          assumptions. Keep this illustrative model separate from reported financial observations.</p>
        <p class="source-note">No reported cash-flow statement, net-debt bridge, or share-count evidence is included.
          A DCF per-share result is unavailable.</p>
      </div>
    </details>
    <details>
      <summary>Peer Read-Through</summary>
      <div class="tool-body">
        <p><strong>Peer A · comparable operating context.</strong> The sample relationship record shows the same
          optical components business and calendar year. Revenue rose 18% from USD 50M to USD 59M. Fogline grew 25%.</p>
        <p><strong>Peer B · operating read-through withheld.</strong> Its segment mix differs. The sample statement
          combines industrial and optical sales without a breakdown. It can still qualify for annual P/E.</p>
        <p class="source-note">Fictional FY2025 statements and peer relationship notes.</p>
      </div>
    </details>
    {_scenario_lab()}
  </div>
  {tables}
  <div class="actions">{_step_link("notes", "Continue to Research Notes")}</div>"""
    return _panel("valuation", "Multiples and assumptions", "Valuation &amp; Peers",
                  f"Compare {_COMPANY} with its sample peers and test a valuation assumption.", content)


def _review_disposition():
    return """<p><strong data-demo-review-status>Pending review</strong></p>
    <p class="monitor-note-text" data-demo-review-reason-line hidden><strong>Reason:</strong> <span data-demo-review-reason></span></p>"""


def _saved_evidence_pair():
    return f"""<section class="surface note-box saved-evidence" id="demo-evidence-pair"
      aria-labelledby="demo-evidence-pair-title">
    <span class="badge">Fictional sample</span>
    <h3 id="demo-evidence-pair-title" tabindex="-1">Saved evidence comparison</h3>
    <p>Two fixed observations of the same Fogline Photonics filing. The newer observation adds a checked
      operating-income line. Reported revenue stays the same.</p>
    <div class="evidence-observations">
      <article data-demo-evidence-observation>
        <p class="eyebrow">Baseline · Saved Feb 13, 2026</p>
        <h4>FICT-FY25-01</h4>
        <p>Jan 1–Dec 31, 2025</p>
        <p class="source-note">Fictional FY2025 annual statement</p>
        <p>USD 120M revenue · Operating income line pending</p>
      </article>
      <article data-demo-evidence-observation>
        <p class="eyebrow">Latest · Saved Feb 20, 2026</p>
        <h4>FICT-FY25-02</h4>
        <p>Jan 1–Dec 31, 2025</p>
        <p class="source-note">Fictional FY2025 annual statement</p>
        <p>USD 120M revenue · USD 17M operating income</p>
      </article>
    </div>
    {_review_disposition()}
    {_step_link("monitor", "Back to Monitor")}
  </section>"""


def _notes():
    content = f"""<div class="tool-list" role="group" aria-label="Research tools">
    <details>
      <summary>Forward View</summary>
      <div class="tool-body">
        <p><strong>Question to test.</strong> Can Fogline keep growing revenue while protecting operating margin?</p>
        <p>FY2025 revenue growth and higher operating income support the question. The next annual statement is
          the check. Compare matching periods and look for any change in segment mix or expenses.</p>
      </div>
    </details>
    <details>
      <summary>Catalysts</summary>
      <div class="tool-body">
        <ul>
          <li><strong>Reviewed · {_SAMPLE_FILING_DATE}.</strong> The fictional FY2025 filing established the baseline.</li>
          <li><strong>Waiting · FY2026 annual statement.</strong> The publication date is unconfirmed.
            Revisit the note after the fictional filing becomes available.</li>
        </ul>
      </div>
    </details>
    <details>
      <summary>Research Decision Lab</summary>
      <div class="tool-body">
        <dl class="decision-lanes">
          <div><dt>Plan</dt><dd>Test whether growth and operating income move together.</dd></div>
          <div><dt>Evidence</dt><dd>Compare the fictional FY2024 and FY2025 statements.</dd></div>
          <div><dt>Invalidation</dt><dd>Revisit the thesis if revenue rises while comparable operating margin falls.</dd></div>
          <div><dt>Scenario</dt><dd>Review the discount-rate sensitivity in {_step_link("valuation", "Valuation &amp; Peers", button=False)}.</dd></div>
          <div><dt>Review trigger</dt><dd>Next fictional annual statement.</dd></div>
          <div><dt>Learning</dt><dd>Record what explained any difference after the filing review.</dd></div>
        </dl>
        <p class="source-note">Use the draft below to carry the review question into Monitor.</p>
      </div>
    </details>
    <details>
      <summary>Research brief</summary>
      <div class="tool-body">
        <p><strong>Business.</strong> FY2025 revenue grew 25.0%; operating income grew faster. Check the next matching period.</p>
        <p><strong>Valuation.</strong> Annual diluted P/E is 24.0×. Review the selected peer evidence before using its comparison.</p>
        <p><strong>Open questions.</strong> Reported cash generation, segment mix, and the next filing date are unavailable.</p>
        <p class="source-note">Fictional research summary. The draft note below is the editable follow-up.</p>
      </div>
    </details>
  </div>
  <div class="note-grid">
    <div class="surface note-box">
      <h3>Draft one follow-up</h3>
      <form class="note-form" id="demo-note-form" data-demo-note-form>
        <label class="field-label" for="demo-note-input">Research note</label>
        <textarea id="demo-note-input" data-demo-note-input rows="4" maxlength="500"
          aria-describedby="demo-note-hint">{_FOLLOW_UP}</textarea>
        <p class="helper" id="demo-note-hint">Edit the example if you like. This note lasts until you reload the demo.</p>
        <button class="button" type="submit" data-demo-pin>Add to Monitor</button>
        <p class="status" id="demo-note-status" data-demo-pin-status role="status"></p>
      </form>
    </div>
    <aside class="surface note-box" aria-label="Research context">
      <span class="badge">Research only</span>
      <h3>What to carry forward</h3>
      <ul>
        <li>Evidence already checked: reported FY 2025 revenue and operating income.</li>
        <li>Next evidence: the next reported annual period.</li>
      </ul>
    </aside>
  </div>
  <div class="actions">{_step_link("monitor", "Open Monitor")}</div>
  {_saved_evidence_pair()}"""
    return _panel("notes", "Thesis and follow-up", "Research Notes",
                  "Turn the evidence into a question you can revisit.", content)


def _sources():
    content = f"""<section class="surface note-box" aria-labelledby="source-register-title">
    <span class="badge">Synthetic provenance</span>
    <h3 id="source-register-title">Evidence used in this company case</h3>
    <p>Every Fogline observation and peer record is fictional and bundled in this offline page.
      Nothing here was fetched from a live company filing or market feed.</p>
    <div class="table-scroll"><table>
      <caption>Context for the observations and assumptions shown in the workspace</caption>
      <thead><tr><th scope="col">Source</th><th scope="col">Scope</th><th scope="col">Use and limitation</th></tr></thead>
      <tbody>
        <tr><th scope="row">Annual statements</th><td>FY2023–FY2025 · Dec 31 year-end · USD</td>
          <td>Revenue, operating income, annual diluted EPS. FY2025 sample dated {_SAMPLE_FILING_DATE}.</td></tr>
        <tr><th scope="row">Quarterly statements</th><td>Q1–Q4 FY2025 · standalone quarters · USD</td>
          <td>Revenue, matching prior-year revenue, and operating income. No cumulative cash flow is treated as a quarter.</td></tr>
        <tr><th scope="row">Daily close records</th><td>{_CLOSE_DATE} · USD</td>
          <td>FICT close USD {_CLOSE:.2f}. The two-peer state dates Peer C to {_PRIOR_CLOSE_DATE} and excludes it.</td></tr>
        <tr><th scope="row">Peer records</th><td>Four candidates · FY2025</td>
          <td>Positive annual diluted EPS, same-day closes, fiscal start/end within 35 days. Three eligible peers are required.</td></tr>
        <tr><th scope="row">Saved evidence pair</th><td>FICT-FY25-01 and FICT-FY25-02</td>
          <td>Fixed observations of the same filing; Monitor preserves the exact pair and its review disposition.</td></tr>
        <tr><th scope="row">Scenario assumptions</th><td>5 years · 8% growth · 10% cash-flow margin · 3% terminal growth</td>
          <td>Illustrative DCF inputs, independent of reported evidence. WACC range: 7%–14%.</td></tr>
      </tbody>
    </table></div>
  </section>
  <section class="surface note-box" aria-labelledby="source-gaps-title">
    <h3 id="source-gaps-title">Evidence still missing</h3>
    <p>Reported operating cash flow, capital expenditure, net debt, share count, segment breakdown,
      and the next filing date are unavailable. Missing observations stay unavailable.</p>
    <p class="source-note">Changing sections reuses this page's bundled evidence. A reload resets draft follow-ups,
      the scenario control, and review status; it does not refresh any source.</p>
  </section>
  <div class="actions">{_step_link("overview", "Return to Overview")}</div>"""
    return _panel("sources", "Source context and gaps", "Data Sources",
                  "Check the period, unit, provenance, and limits behind each part of the research.", content)


def _monitor():
    content = f"""<section class="surface monitor-note" aria-labelledby="demo-evidence-follow-up-title">
    <span class="badge">Fictional sample</span>
    <h3 id="demo-evidence-follow-up-title">Sample evidence follow-up</h3>
    <p>Fogline Photonics · FY2025 annual statement</p>
    {_review_disposition()}
    <a class="button" href="#demo-evidence-pair">Review saved evidence</a>
    <details data-demo-review-controls hidden>
      <summary>Record a disposition</summary>
      <form class="note-form" data-demo-review-form autocomplete="off">
        <fieldset class="review-choices">
          <legend class="field-label">Disposition</legend>
          <div class="actions">
            <label><input type="radio" name="disposition" value="Reviewed" required> Reviewed</label>
            <label><input type="radio" name="disposition" value="Still open" required> Still open</label>
          </div>
        </fieldset>
        <label class="field-label" for="demo-review-reason">Reason</label>
        <textarea id="demo-review-reason" rows="2" maxlength="500" required
          aria-describedby="demo-review-hint"></textarea>
        <p class="helper" id="demo-review-hint">A reason is required. Review status and reason reset on reload.</p>
        <button class="button" type="submit">Save disposition</button>
        <p class="status" role="status" data-demo-review-feedback></p>
      </form>
    </details>
    <noscript><p class="source-note">Recording a disposition requires scripts.</p></noscript>
  </section>
  <div class="surface note-box" id="demo-monitor-empty" data-demo-monitor-empty>
    <span class="badge">Follow-up queue</span>
    <h3>No personal follow-up yet</h3>
    <p class="source-note">Add a note from Research Notes to see it here.</p>
    {_step_link("notes", "Return to Research Notes")}
  </div>
  <article class="surface monitor-note" id="demo-monitor-note" data-demo-monitor-item hidden>
    <span class="badge badge--warning">Waiting on evidence</span>
    <h3>{_COMPANY} · {_TICKER}</h3>
    <p id="demo-monitor-note-text" class="monitor-note-text" data-demo-monitor-note></p>
    <p class="source-note">Trigger: next reported annual period. This follow-up lasts until reload.</p>
    {_step_link("notes", "Return to Research Notes")}
  </article>
  <div class="actions">{_step_link("overview", "Reopen Company Workbench", button=False)}</div>"""
    return _panel("monitor", "Follow-up queue", "Monitor",
                  "Review a saved evidence comparison and revisit the question you carried forward.", content)


def build_demo_html():
    script = _SCRIPT_PATH.read_text(encoding="utf-8")
    digest = b64encode(sha256(script.encode("utf-8")).digest()).decode("ascii")
    available_summary, available_comparison, available_table = _peer_scenario(False)
    withheld_summary, withheld_comparison, withheld_table = _peer_scenario(True)
    steps = "".join(
        f'<li><a href="#{step}" data-demo-section="{step}" data-demo-go="{step}">'
        f'<span class="step-number" aria-hidden="true">{number}</span>{label}</a></li>'
        for number, (step, label) in enumerate(_STEPS, start=1)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <title>{escape(_TITLE)}</title>
  <meta name="description" content="{escape(_DESCRIPTION, quote=True)}">
  <meta property="og:title" content="{escape(_TITLE, quote=True)}">
  <meta property="og:description" content="{escape(_DESCRIPTION, quote=True)}">
  <style>{_STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#demo-main">Skip to demo content</a>
  <header class="masthead">
    <div class="masthead-inner">
      <div class="brand"><span class="brand-mark" aria-hidden="true">SR</span>
        <div><p class="eyebrow">Guided product demo</p><h1>Stock Research Command Center</h1></div>
      </div>
      <p class="badge">Synthetic data · Fictional company</p>
    </div>
  </header>
  <div class="layout">
    <aside class="workspace-rail" aria-label="Workspace navigation">
    <nav class="steps" aria-label="Research workflow">
      <p class="steps-title eyebrow">Research workflow</p>
      <ul class="workflow-links">
        <li><a href="#discover" data-demo-workflow="discover" data-demo-go="discover">Company Search</a></li>
        <li><a href="#monitor" data-demo-workflow="monitor" data-demo-go="monitor">Monitor</a></li>
      </ul>
    </nav>
    <nav class="steps" aria-label="Company sections">
      <p class="steps-title eyebrow">Company Workbench</p>
      <ol>{steps}</ol>
      <p class="scope-note">A guided research case. Search and follow-up work entirely in this page.</p>
    </nav>
    </aside>
    <main id="demo-main" tabindex="-1">
      <header class="company-heading" data-demo-company-heading>
        <p class="eyebrow">{_TICKER} · Company Workbench</p>
        <h2>{_COMPANY}</h2>
        <p>Photonics and optical components · Fictional research case</p>
      </header>
      {_discover()}
      {_overview(available_summary + withheld_summary)}
      {_financials()}
      {_valuation(available_comparison + withheld_comparison, available_table + withheld_table)}
      {_notes()}
      {_sources()}
      {_monitor()}
    </main>
  </div>
  <footer class="page-footer">Stock Research Command Center · Synthetic research case</footer>
  <script>{script}</script>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Path for the standalone HTML file.")
    args = parser.parse_args(argv)
    args.output.write_text(build_demo_html(), encoding="utf-8")


if __name__ == "__main__":
    main()
