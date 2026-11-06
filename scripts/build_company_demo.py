"""Build a standalone company research page using only synthetic examples."""

import argparse
from pathlib import Path

from src.company_answer_summary import COMPANY_ANSWERS_STYLE, company_answers_html


_TITLE = "Stock Research Command Center · 公司研究演示"
_DESCRIPTION = "Stock Research Command Center 的合成数据演示。查看虚构公司的收盘价、财报变化和同行估值。"
_PRICE_DATE = "2026-10-30"
_ANSWERS = (
    {
        "key": "price",
        "title": "最近收盘",
        "value": "USD 48.00",
        "context": f"{_PRICE_DATE} · 已完成收盘",
        "evidence": (f"示例日线收盘记录，{_PRICE_DATE}，48.00 USD。",),
    },
    {
        "key": "financial",
        "title": "财报变化",
        "value": "营收 USD 1.20 亿",
        "context": "截至 2025-12-31 · 较上财年增加",
        "evidence": (
            "示例年度财务记录。2025 年营收为 1.20 亿 USD，2024 年为 0.96 亿 USD。",
            "2025 年度摊薄 EPS 为 2.00 USD，用于示例估值。",
        ),
    },
)
_VALUATION = {
    "key": "valuation",
    "title": "同行估值",
    "value": "24.0× · 同行中位 20.0×",
    "context": "3 家符合 · 高于同行中位数 20%",
    "evidence": (
        f"本公司 P/E 为 {_PRICE_DATE} 的示例收盘价 48.00 USD 除以年度摊薄 EPS 2.00 USD。",
        "三家参照使用同日收盘价与相同财年。参照 A、B、C 的收盘价分别为 36.00、40.00、44.00 USD，摊薄 EPS 均为 2.00 USD。",
        "同行中位数取三个 P/E 的中间值。相对差异按 24.0 ÷ 20.0 − 1 计算。",
    ),
}
_WITHHELD = {
    "key": "valuation",
    "title": "同行估值",
    "value": "同行比较暂缺",
    "context": "本公司 24.0× · 2 家符合 · 至少需 3 家",
    "evidence": (
        f"参照 A 和参照 B 的示例收盘日均为 {_PRICE_DATE}，年度摊薄 EPS 口径可比。",
        "参照 C 的示例收盘日为 2026-10-29，未通过同日收盘价核对。",
        "达到三家合格参照后，才显示同行中位数及相对倍数差异。",
    ),
}
_PAGE_STYLE = """
body { margin: 0; background: #f5f7f6; color: #1c302a;
       font: 1rem/1.5 system-ui, sans-serif; }
main { max-width: 65rem; margin-inline: auto; padding: 1.5rem 1.25rem; }
h1 { font-size: clamp(1.65rem, 4vw, 2.25rem); line-height: 1.2; margin: .2rem 0; }
.demo-label { color: #275d45; font-weight: 700; }
.demo-label, .demo-note { margin: 0; }
.demo-controls { margin: 1rem 0; padding: 0; border: 0; min-inline-size: 0; }
.demo-controls legend { padding: 0; font-size: .9rem; font-weight: 650; }
.demo-controls label { display: inline-flex; align-items: center; gap: .45rem;
                       min-height: 2.75rem; margin-inline-end: .8rem; cursor: pointer; }
.demo-controls input { margin: 0; accent-color: #275d45; }
.demo-controls input:focus-visible { outline: 2px solid #275d45; outline-offset: 3px; }
.demo-state--withheld { display: none; }
.demo-controls:has(#demo-withheld:checked) ~ .demo-state--available { display: none; }
.demo-controls:has(#demo-withheld:checked) ~ .demo-state--withheld { display: block; }
"""


def build_demo_html():
    available = company_answers_html((*_ANSWERS, _VALUATION))
    withheld = company_answers_html((*_ANSWERS, _WITHHELD))
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <title>{_TITLE}</title>
  <meta name="description" content="{_DESCRIPTION}">
  <meta property="og:title" content="{_TITLE}">
  <meta property="og:description" content="{_DESCRIPTION}">
  <style>{COMPANY_ANSWERS_STYLE}{_PAGE_STYLE}</style>
</head>
<body>
  <main>
    <header>
      <p class="demo-label">合成数据演示 · 虚构公司</p>
      <h1>雾岬光路</h1>
      <p class="demo-note">公司、价格、财务和同行数据均为示例。</p>
    </header>
    <fieldset class="demo-controls">
      <legend>切换同行样本</legend>
      <label><input type="radio" name="demo-scenario" checked> 3 家符合</label>
      <label><input type="radio" name="demo-scenario" id="demo-withheld"> 2 家符合</label>
    </fieldset>
    <div class="demo-state--available">{available}</div>
    <div class="demo-state--withheld">{withheld}</div>
  </main>
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
