"""Build the public AMD filing case as a standalone HTML page."""

import argparse
from pathlib import Path

from scripts.build_company_demo import _STYLE


_ACCESSION = "0000002488-26-000191"
_FILING = "https://www.sec.gov/Archives/edgar/data/2488/000000248826000191/amd-20260926.htm"
# Published values are derived metrics. Each row points to directly reported three-month GAAP inputs.
_QUARTERS = (
    ("Q4 FY2025", "Dec 27, 2025", 100.0, 17.1, "8-K exhibit",
     "https://www.sec.gov/Archives/edgar/data/2488/000000248826000014/q42025991.htm"),
    ("Q1 FY2026", "Mar 28, 2026", 99.8, 14.4, "10-Q",
     "https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm"),
    ("Q2 FY2026", "Jun 27, 2026", 112.3, 17.3, "10-Q",
     "https://www.sec.gov/Archives/edgar/data/2488/000000248826000123/amd-20260627.htm"),
    ("Q3 FY2026", "Sep 26, 2026", 130.3, 21.2, "10-Q", _FILING),
)
_REVENUE_CHANGE = 44.7
_PRIOR_Q3_MARGIN = 13.7
_MARGIN_CHANGE = 7.4
_SEGMENT_CHANGES = (("Data Center", 96.9, 63.9), ("Client and Gaming", -8.1, 27.8), ("Embedded", 29.4, 8.3))
_PRIOR_DATA_CENTER_SHARE = 47.0
# Continuing operations only, from the nine-month cash flow statement in the Q3 10-Q.
_CASH_AFTER_PPE = (3.437, 4.678)
_PPE_SHARE = (18.0, 28.3)
_CASE_STYLE = """
.case-valuation { display: block; }
.case-valuation details { margin-top: .28rem; padding-inline: 0; background: transparent; border: 0; }
.case-valuation summary { min-height: 2.75rem; font-size: .88rem; text-decoration: underline; }
.case-valuation details p { margin-top: .4rem; }
.case-source { display: flex; flex-wrap: wrap; gap: .25rem .7rem; }
.case-source a { font-weight: 750; }
.case-insight { display: grid; gap: .25rem; padding: .85rem 1rem; border-left: .27rem solid #28634f; }
.case-insight h3 { font-size: 1.05rem; }
.case-cash { display: grid; gap: .55rem; }
.case-cash-result { display: flex; flex-wrap: wrap; gap: .4rem 1.7rem; }
.case-cash-result > div { min-width: 8rem; }
.case-cash-result strong { font-size: 1.35rem; }
.case-quarter-table :is(th,td) { padding-inline: .35rem; }
#filing-source, .case-quarter-table { overflow-wrap: anywhere; }
@media (max-width: 600px) {
  .case-nav-extra { display: none; }
  .case-quarter-table :is(th,td) { padding-inline: .2rem; font-size: .78rem; }
}
"""


def _margin_chart():
    bars = []
    for index, (quarter, _, _, margin, _, _) in enumerate(_QUARTERS):
        x = 36 + index * 94
        height = margin * 5
        y = 137 - height
        bars.append(f'<rect class="chart-bar" x="{x}" y="{y:g}" width="54" height="{height:g}" rx="5"/>'
                    f'<text class="chart-value" x="{x+27}" y="{y-7:g}" text-anchor="middle">{margin:.1f}%</text>'
                    f'<text x="{x+27}" y="157" text-anchor="middle">{quarter}</text>')
    description = ", ".join(f"{quarter} {margin:.1f}%" for quarter, _, _, margin, _, _ in _QUARTERS)
    return f"""<figure class="surface chart">
  <h3>Quarterly operating margin</h3>
  <svg viewBox="0 0 412 163" role="img" aria-labelledby="margin-title margin-desc">
    <title id="margin-title">Quarterly operating margin</title>
    <desc id="margin-desc">{description}</desc>
    <path class="chart-line" d="M18 137H394"/>
    {''.join(bars)}
  </svg>
  <figcaption>GAAP operating income divided by net revenue.</figcaption>
</figure>"""


def build_amd_demo_html():
    segments = "".join(f'<tr><th scope="row">{name}</th><td>{change:+.1f}%</td><td>{share:.1f}%</td></tr>'
                       for name, change, share in _SEGMENT_CHANGES)
    quarters = "".join(f'<tr><th scope="row">{quarter}</th><td>{end}</td><td>{revenue:.1f}</td><td>{margin:.1f}%</td>'
                       f'<td><a href="{source}" aria-label="{quarter} {form} on SEC EDGAR">{form}</a></td></tr>'
                       for quarter, end, revenue, margin, form, source in _QUARTERS)
    prior_cash, latest_cash = _CASH_AFTER_PPE
    cash_change = (latest_cash / prior_cash - 1) * 100
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <title>AMD Filing Case | Stock Research Command Center</title>
  <meta name="description" content="Research AMD’s Q3 FY2026 growth drivers, quarterly trends, cash generation, and an example Monitor follow-up.">
  <style>{_STYLE}{_CASE_STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#case-main">Skip to AMD research</a>
  <header class="masthead">
    <div class="masthead-inner">
      <div class="brand"><span class="brand-mark" aria-hidden="true">SR</span>
        <div><p class="eyebrow">Company Workbench</p><h1>Stock Research Command Center</h1></div>
      </div>
      <p class="badge">Real company · SEC filing case</p>
    </div>
  </header>
  <div class="layout">
    <nav class="steps" aria-label="Research case">
      <p class="steps-title eyebrow">Research case</p>
      <ol>
        <li><a href="#case-main" aria-current="page">Financial overview</a></li>
        <li><a href="#quarterly-trends">Quarterly trends</a></li>
        <li><a href="#cash-generation">Cash flow</a></li>
        <li class="case-nav-extra"><a href="#peer-valuation">Peer valuation</a></li>
        <li><a href="#monitor-follow-up">Monitor follow-up</a></li>
        <li class="case-nav-extra"><a href="#filing-source">Filing source</a></li>
        <li class="case-nav-extra"><a href="./">Guided demo</a></li>
      </ol>
      <p class="scope-note">A dated, read-only company research case.</p>
    </nav>
    <main id="case-main" class="panel" tabindex="-1">
      <header class="panel-intro">
        <p class="eyebrow">AMD · Q3 FY2026 · SEC Form 10-Q</p>
        <h2>Advanced Micro Devices</h2>
        <p class="case-source"><span>Quarter ended Sep 26, 2026</span><span>· Filed Nov 4, 2026</span>
          <a href="#filing-source">Filing &amp; calculations</a></p>
      </header>
      <div class="metrics" aria-label="Quarterly results">
        <article class="metric"><p class="metric-label">Revenue growth</p>
          <p class="metric-value">{_REVENUE_CHANGE:+.1f}%</p><p class="metric-context">Year over year</p></article>
        <article class="metric"><p class="metric-label">Operating margin</p>
          <p class="metric-value">{_QUARTERS[-1][3]:.1f}%</p><p class="metric-context">{_MARGIN_CHANGE:+.1f} pp year over year</p></article>
        <article class="metric"><p class="metric-label">Data Center growth</p>
          <p class="metric-value">{_SEGMENT_CHANGES[0][1]:+.1f}%</p><p class="metric-context">Revenue year over year</p></article>
        <article id="peer-valuation" class="metric peer-callout case-valuation" aria-labelledby="peer-case-title">
          <h3 id="peer-case-title" class="peer-callout-title">Peer valuation</h3>
          <p class="peer-callout-answer">Peer comparison withheld</p>
          <p class="metric-context">Same-day closes needed</p>
          <details><summary>View why</summary>
            <p class="metric-context">The project uses its price feed for personal research only. A public annual diluted P/E
              comparison requires approved same-day closes for AMD and at least three eligible peers.</p>
          </details>
        </article>
      </div>
      <section class="surface case-insight" aria-labelledby="driver-title">
        <h3 id="driver-title">What drove the quarter</h3>
        <p>Data Center drove the revenue increase. Its share rose to <strong>{_SEGMENT_CHANGES[0][2]:.1f}%</strong>
          from {_PRIOR_DATA_CENTER_SHARE:.1f}% a year earlier, while Client and Gaming revenue fell
          {abs(_SEGMENT_CHANGES[1][1]):.1f}%.</p>
      </section>
      <div class="trend-grid">
        {_margin_chart()}
        <section class="surface" aria-labelledby="segment-title">
          <h3 id="segment-title">Segment revenue growth</h3>
          <table class="numbers">
            <caption>Q3 FY2026 vs. Q3 FY2025</caption>
            <thead><tr><th scope="col">Segment</th><th scope="col">YoY change</th><th scope="col">Revenue share</th></tr></thead>
            <tbody>{segments}</tbody>
          </table>
        </section>
      </div>
      <section id="quarterly-trends" class="surface" aria-labelledby="quarterly-title">
        <h3 id="quarterly-title">Quarterly trends</h3>
        <table class="numbers case-quarter-table">
          <caption>Four directly reported quarters. Revenue index uses Q4 FY2025 = 100.</caption>
          <thead><tr><th scope="col">Quarter</th><th scope="col">Period end</th><th scope="col">Revenue index</th>
            <th scope="col">GAAP margin</th><th scope="col">SEC source</th></tr></thead>
          <tbody>{quarters}</tbody>
        </table>
      </section>
      <section id="cash-generation" class="surface case-cash" aria-labelledby="cash-title">
        <h3 id="cash-title">Cash generation</h3>
        <p class="metric-context">Continuing operations · Nine months ended Sep 26, 2026 vs. Sep 27, 2025</p>
        <div class="case-cash-result">
          <div><p class="metric-label">Operating cash after PP&amp;E</p><p><strong>USD {latest_cash:.3f}B</strong></p></div>
          <div><p class="metric-label">Prior nine months</p><p><strong>USD {prior_cash:.3f}B</strong></p></div>
          <div><p class="metric-label">Year over year</p><p><strong>{cash_change:+.1f}%</strong></p></div>
        </div>
        <p>Cash purchases of property and equipment used {_PPE_SHARE[1]:.1f}% of operating cash flow, up from
          {_PPE_SHARE[0]:.1f}% a year earlier.</p>
        <details><summary>View cash flow calculation</summary>
          <p>Subtract cash purchases of property and equipment from operating cash flow. Both inputs come from
            continuing operations in the nine-month columns of the <a href="{_FILING}">Q3 Form 10-Q</a>.</p>
        </details>
      </section>
      <section id="monitor-follow-up" class="surface monitor-note" aria-labelledby="monitor-title">
        <p class="badge">Example · Open question</p>
        <h3 id="monitor-title">Sample Monitor follow-up</h3>
        <p><strong>Does Data Center growth keep translating into stronger cash generation?</strong></p>
        <p>At the next AMD filing, compare Data Center’s revenue share and cash after PP&amp;E using matching
          periods. Review working capital and cash spending if the two trends diverge.</p>
        <div class="actions"><a href="#cash-generation">Review the baseline</a>
          <a href="./#notes">Try adding a follow-up in the guided demo</a></div>
      </section>
      <details id="filing-source"><summary>Filing &amp; calculations</summary>
        <p><a href="{_FILING}">Read AMD’s Form 10-Q on SEC EDGAR</a> · Accession {_ACCESSION}</p>
        <ul>
          <li>The consolidated statements and Note 4 compare the three months ended Sep 26, 2026
            with the three months ended Sep 27, 2025.</li>
          <li>Revenue growth is current divided by prior revenue minus one. Segment share is segment revenue divided
            by total net revenue.</li>
          <li>GAAP operating margin is operating income divided by net revenue. The Q3 FY2025 margin was
            {_PRIOR_Q3_MARGIN:.1f}%. The year-over-year margin change uses the unrounded ratios.</li>
          <li>The revenue index divides each quarter's net revenue by directly reported Q4 FY2025 net revenue,
            then multiplies by 100. The Q4 figures come from the earnings release AMD furnished as Exhibit 99.1
            to Form 8-K. The quarterly table links to each source.</li>
        </ul>
      </details>
    </main>
  </div>
  <footer class="page-footer">Stock Research Command Center · Historical filing case</footer>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Path for the standalone HTML file.")
    args = parser.parse_args()
    args.output.write_text(build_amd_demo_html(), encoding="utf-8")


if __name__ == "__main__":
    main()
