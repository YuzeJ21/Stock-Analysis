"""Real framework-wrapper and dark-appearance regression for readable research actions."""
from pathlib import Path
import re


def _contrast(foreground,background):
 def luminance(text):
  values=[float(x)/255 for x in re.findall(r'[\d.]+',text)[:3]]
  values=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in values]
  return sum(a*b for a,b in zip(values,[.2126,.7152,.0722]))
 a,b=sorted([luminance(foreground),luminance(background)])
 return (b+.05)/(a+.05)


def test_research_action_labels_remain_readable_in_light_and_dark_system_appearance(tmp_path):
 from playwright.sync_api import sync_playwright
 from src.public_performance_gate import _local_demo_server
 root=Path(__file__).resolve().parents[1]
 (tmp_path/'src').mkdir()
 (tmp_path/'src/dashboard.py').write_text('import sys\nimport streamlit as st\nsys.path.insert(0,'+repr(str(root))+')\nfrom src.dashboard import apply_dashboard_theme,render_research_workspace_styles\napply_dashboard_theme()\nrender_research_workspace_styles()\nwith st.container(key="company-sec-annual-check"):\n st.button("Check SEC annual facts",key="company-sec-annual-refresh-FICT",help="Synthetic read-only source check")\nst.button("Check latest SEC filing",key="company-exact-filing-refresh-FICT")\nst.button("Check listing and issuer type",key="company-security-refresh-FICT")\nst.button("Check online price history",key="company-online-price-refresh-FICT")\nst.button("Open evidence and analysis modules")\n')
 with _local_demo_server(tmp_path,timeout_seconds=30) as base:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True)
   failures=[]
   for scheme in ('light','dark'):
    page=browser.new_page(color_scheme=scheme,viewport={'width':390,'height':844})
    page.goto(base,wait_until='domcontentloaded')
    page.get_by_role('button',name='Check online price history',exact=True).wait_for(timeout=15000)
    page.get_by_role('button',name='Check SEC annual facts',exact=True).hover()
    rows=page.evaluate('''() => [...document.querySelectorAll('[data-testid="stButton"] button')].filter(b=>{const r=b.getBoundingClientRect();return r.width>0&&r.height>0}).map(b=>({label:b.textContent,background:getComputedStyle(b).backgroundColor,foreground:getComputedStyle(b.querySelector('p')||b).color,height:b.getBoundingClientRect().height}))''')
    assert len(rows)>=5
    for row in rows:
     background='rgb(255,255,255)' if row['background']=='rgba(0, 0, 0, 0)' else row['background']
     if _contrast(row['foreground'],background)<4.5 or row['height']<44:failures.append({'appearance':scheme,'contrast':_contrast(row['foreground'],background),**row})
    page.close()
   browser.close()
   assert not failures,failures
