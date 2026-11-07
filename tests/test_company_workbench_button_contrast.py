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
 (tmp_path/'src/dashboard.py').write_text('import sys\nimport streamlit as st\nsys.path.insert(0,'+repr(str(root))+')\nfrom src.dashboard import apply_dashboard_theme,render_research_workspace_styles\napply_dashboard_theme()\nrender_research_workspace_styles()\nst.button("Combined company update",key="company-refresh-all",type="primary")\nfrom src.company_workbench_sections import workbench_header_html,workbench_projection\nst.markdown(workbench_header_html("FICT",workbench_projection("FICT",{},{}),True),unsafe_allow_html=True)\nwith st.container(key="company-sec-annual-check"):\n st.button("Check SEC annual facts",key="company-sec-annual-refresh-FICT",help="Synthetic read-only source check")\nst.button("Check latest SEC filing",key="company-exact-filing-refresh-FICT")\nst.button("Check listing and issuer type",key="company-security-refresh-FICT")\nst.button("Check online price history",key="company-online-price-refresh-FICT")\nst.button("Open evidence and analysis modules")\nwith st.form("synthetic-search"):\n st.text_input("Search company",value="FICT")\n st.form_submit_button("Search SEC now")\nst.download_button("Download company brief",data="Synthetic company brief",file_name="example.txt",key="company-workbench-html-test")\nst.download_button("Unrelated download",data="Synthetic unrelated output",file_name="other.txt",key="unrelated-download")\n')
 with _local_demo_server(tmp_path,timeout_seconds=30) as base:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True)
   failures=[]
   for scheme in ('light','dark'):
    page=browser.new_page(color_scheme=scheme,viewport={'width':390,'height':844})
    page.goto(base,wait_until='domcontentloaded')
    page.get_by_role('button',name='Check online price history',exact=True).wait_for(timeout=15000)
    page.get_by_role('button',name='Check SEC annual facts',exact=True).hover()
    rows=page.evaluate('''() => [...document.querySelectorAll('.company-integrated-header a, [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button, [class*="st-key-company-workbench-html-"] [data-testid="stDownloadButton"] button')].filter(b=>{const r=b.getBoundingClientRect();return r.width>0&&r.height>0}).map(b=>({label:b.textContent,background:getComputedStyle(b).backgroundColor,foreground:getComputedStyle(b.querySelector('p')||b).color,height:b.getBoundingClientRect().height}))''')
    assert {row['label'].strip() for row in rows} == {
     'Combined company update','Check SEC annual facts','Check latest SEC filing',
     'Check listing and issuer type','Check online price history','Open evidence and analysis modules',
     'Search SEC now','Download company brief',
    }
    assert any("Search SEC now" in row["label"] for row in rows)
    assert any("Download company brief" in row["label"] for row in rows)
    assert all("Unrelated download" not in row["label"] for row in rows)
    for row in rows:
     background='rgb(255,255,255)' if row['background']=='rgba(0, 0, 0, 0)' else row['background']
     if _contrast(row['foreground'],background)<4.5 or row['height']<44:failures.append({'appearance':scheme,'contrast':_contrast(row['foreground'],background),**row})
    page.close()
   browser.close()
   assert not failures,failures


def test_actual_company_refresh_popover_has_readable_unclipped_labels_at_phone_widths(tmp_path):
 from playwright.sync_api import sync_playwright
 from src.public_performance_gate import _local_demo_server
 root=Path(__file__).resolve().parents[1]
 (tmp_path/'src').mkdir()
 (tmp_path/'src/dashboard.py').write_text(
  'import sys\nimport streamlit as st\nsys.path.insert(0,'+repr(str(root))+')\n'
  'from src.dashboard import apply_dashboard_theme,render_research_workspace_styles\n'
  'from src.company_workbench_ui import render_integrated_company\n'
  'apply_dashboard_theme()\nrender_research_workspace_styles()\n'
  'render_integrated_company(st,"FICT",profile_scope="synthetic",saved_available=False,render_saved=lambda section:None,render_sources=lambda bundle:None)\n')
 failures=[]
 with _local_demo_server(tmp_path,timeout_seconds=30) as base:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True)
   for width in (1280,390,320):
    for scheme in ('light','dark'):
     page=browser.new_page(color_scheme=scheme,viewport={'width':width,'height':844})
     page.goto(base,wait_until='domcontentloaded')
     control=page.get_by_role('button',name='Refresh options',exact=True)
     control.wait_for(timeout=15000)
     for hovered in (False,True):
      if hovered:control.hover()
      row=control.evaluate('''b=>{const p=b.querySelector('p');return {background:getComputedStyle(b).backgroundColor,foreground:getComputedStyle(p||b).color,height:b.getBoundingClientRect().height,labelWidth:p.clientWidth,labelScroll:p.scrollWidth}}''')
      ratio=_contrast(row['foreground'],row['background'])
      if ratio<4.5 or row['height']<44 or row['labelScroll']>row['labelWidth']+1:
       failures.append({'width':width,'appearance':scheme,'hovered':hovered,'contrast':ratio,**row})
     assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
     control.click()
     assert page.get_by_role('button',name='Financials only',exact=True).is_visible()
     assert page.get_by_role('button',name='Prices only',exact=True).is_visible()
     page.close()
   browser.close()
 assert not failures,failures
