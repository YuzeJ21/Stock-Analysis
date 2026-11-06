"""Build the public AMD filing case as a standalone HTML page."""

import argparse
from pathlib import Path

from scripts.build_company_demo import _STYLE


_ACCESSION = "0000002488-26-000191"
_FILING = "https://www.sec.gov/Archives/edgar/data/2488/000000248826000191/amd-20260926.htm"
# Derived from the three-month columns in the consolidated statements and Note 4.
_REVENUE_CHANGE = 44.7
_MARGINS = (("Q3 FY2025", 13.7), ("Q3 FY2026", 21.2))
_MARGIN_CHANGE = 7.4
_SEGMENT_CHANGES = (("Data Center", 96.9), ("Client and Gaming", -8.1), ("Embedded", 29.4))
_CASE_STYLE = """
.case-valuation { display: block; }
.case-valuation details { margin-top: .28rem; padding-inline: 0; background: transparent; border: 0; }
.case-valuation summary { min-height: 2.75rem; font-size: .88rem; text-decoration: underline; }
.case-valuation details p { margin-top: .4rem; }
.case-source { display: flex; flex-wrap: wrap; gap: .25rem .7rem; }
.case-source a { font-weight: 750; }
#filing-source { overflow-wrap: anywhere; }
"""


def _margin_chart():
    bars = []
    for x, (quarter, margin) in zip((55, 201), _MARGINS):
        height = margin * 5.5
        y = 170 - height
        bars.append(f'<rect class="chart-bar" x="{x}" y="{y:g}" width="72" height="{height:g}" rx="5"/>'
                    f'<text class="chart-value" x="{x+36}" y="{y-8:g}" text-anchor="middle">{margin:.1f}%</text>'
                    f'<text x="{x+36}" y="190" text-anchor="middle">{quarter}</text>')
    description = ", ".join(f"{quarter} {margin:.1f}%" for quarter, margin in _MARGINS)
    return f"""<figure class="surface chart">
  <h3>Operating margin</h3>
  <svg viewBox="0 0 330 196" role="img" aria-labelledby="margin-title margin-desc">
    <title id="margin-title">Quarterly operating margin</title>
    <desc id="margin-desc">{description}</desc>
    <path class="chart-line" d="M18 170H314"/>
    {''.join(bars)}
  </svg>
  <figcaption>Calculated as GAAP operating income divided by net revenue.</figcaption>
</figure>"""


def build_amd_demo_html():
    segments = "".join(f'<tr><th scope="row">{name}</th><td>{change:+.1f}%</td></tr>'
                       for name, change in _SEGMENT_CHANGES)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <title>AMD Filing Case | Stock Research Command Center</title>
  <meta name="description" content="Review AMD’s Q3 FY2026 revenue growth, operating margin, and peer valuation evidence gap.">
  <style>{_STYLE}{_CASE_STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#case-main">Skip to AMD research</a>
  <header class="masthead">
    <div class="masthead-inner">
      <div class="brand"><span class="brand-mark" aria-hidden="true">SR</span>
        <div><p class="eyebrow">Company Workbench</p><h1>Stock Research Command Center</h1></div>
      </div>
      <p class="badge">Real company · SEC filing snapshot</p>
    </div>
  </header>
  <div class="layout">
    <nav class="steps" aria-label="Research case">
      <p class="steps-title eyebrow">Research case</p>
      <ol>
        <li><a href="#case-main" aria-current="page">Financial overview</a></li>
        <li><a href="#peer-valuation">Peer valuation</a></li>
        <li><a href="#filing-source">Filing source</a></li>
        <li><a href="./">Guided demo</a></li>
      </ol>
      <p class="scope-note">A dated, read-only example based on one SEC filing.</p>
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
          <p class="metric-value">{_MARGINS[-1][1]:.1f}%</p><p class="metric-context">{_MARGIN_CHANGE:+.1f} pp year over year</p></article>
        <article class="metric"><p class="metric-label">Data Center growth</p>
          <p class="metric-value">{_SEGMENT_CHANGES[0][1]:+.1f}%</p><p class="metric-context">Revenue year over year</p></article>
        <article id="peer-valuation" class="metric peer-callout case-valuation" aria-labelledby="peer-case-title">
          <h3 id="peer-case-title" class="peer-callout-title">Peer valuation</h3>
          <p class="peer-callout-answer">Peer comparison withheld</p>
          <p class="metric-context">Same-day closes needed</p>
          <details><summary>View why</summary>
            <p class="metric-context">The price feed is cleared for personal research only. This public case has no approved
              same-day closes to compare annual diluted P/E for AMD and at least three eligible peers.</p>
          </details>
        </article>
      </div>
      <div class="trend-grid">
        {_margin_chart()}
        <section class="surface" aria-labelledby="segment-title">
          <h3 id="segment-title">Segment revenue growth</h3>
          <table class="numbers">
            <caption>Q3 FY2026 vs. Q3 FY2025</caption>
            <thead><tr><th scope="col">Segment</th><th scope="col">Change</th></tr></thead>
            <tbody>{segments}</tbody>
          </table>
        </section>
      </div>
      <details id="filing-source"><summary>Filing &amp; calculations</summary>
        <p><a href="{_FILING}">Read AMD’s Form 10-Q on SEC EDGAR</a> · Accession {_ACCESSION}</p>
        <ul>
          <li>The consolidated statements and Note 4 compare the three months ended Sep 26, 2026
            with the three months ended Sep 27, 2025.</li>
          <li>Revenue growth is current divided by prior revenue minus one. Operating margin is operating income
            divided by net revenue. The margin change uses the unrounded ratios.</li>
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
