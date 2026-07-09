from pathlib import Path
import re


PUBLIC_V1_ROUTE = (
    "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History"
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_product_tour_matches_v1_public_route_model():
    readme = _read("README.md")

    assert "## Pilot In 60 Seconds" in readme
    assert "Open `http://localhost:8501/?mode=public`" in readme
    assert "Screenshots are product evidence only; they do not prove data freshness or unlock blocked inputs." in readme
    assert "Use `make status-check TOP_N=5` for current local readiness counts." in readme
    assert "Start with the five public paths" in readme
    assert "| Home |" in readme
    assert "| Stock Selector |" in readme
    assert "| Single-Stock Report |" in readme
    assert "| Data Health |" in readme
    assert "| Proof History |" in readme
    assert "| Stock Selector | You want to filter readiness-backed candidates" in readme
    assert "| Proof History | You want to see the proof ledger" in readme
    assert "| Proof History |" in readme and "| `Proof History` |" in readme
    assert PUBLIC_V1_ROUTE in readme
    assert "Data Health source-proof lane" not in readme
    assert "Proof History is the public proof-inspection surface" not in readme
    assert "Operator context" in readme
    assert "Home readiness snapshot ->" not in readme
    assert "Home readiness snapshot -> Single-Stock Report -> Data Health source-proof lane -> proof history" not in readme
    assert "Start with the three paths" not in readme


def test_readme_and_roadmap_name_pilot_operator_runbook():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")

    assert "Pilot packaging is read-only first" in readme
    assert "make pilot-share-brief" in readme
    assert "does not refresh data or unlock blocked inputs" in readme
    assert "Provider setup is only an activation boundary" in readme

    assert "Pilot Operator Runbook V1" in roadmap
    assert "share gate, source gate, provider setup, reviewed one-ticker smoke command, validate/preview, packet, and hygiene" in roadmap
    assert "without reopening broad proof loops" in roadmap


def test_roadmap_current_counts_are_live_command_gated():
    roadmap = _read("ROADMAP.md")

    assert "Broad-universe command center visibility for the tracked master universe" in roadmap
    assert "Master universe rows: use `make project-status` or `make status-check TOP_N=5`" in roadmap
    assert "Active research rows: use `make project-status` or the dashboard Home page" in roadmap
    assert "whole tracked universe is analysis-ready" in roadmap
    assert "tracked master universe, active universe, and analysis-ready subset" in roadmap
    assert "current 3,538-ticker" not in roadmap
    assert "Master universe rows: 3,538" not in roadmap
    assert "whole 3,538-ticker universe" not in roadmap


def test_public_docs_do_not_reintroduce_old_three_path_navigation():
    docs = {
        "README.md": _read("README.md"),
        "ROADMAP.md": _read("ROADMAP.md"),
        "docs/DATA_STRATEGY.md": _read("docs/DATA_STRATEGY.md"),
        "docs/PUBLIC_DEMO_WALKTHROUGH.md": _read("docs/PUBLIC_DEMO_WALKTHROUGH.md"),
    }

    for body in docs.values():
        assert "three main paths" not in body
        assert "three simple paths" not in body
        assert "More pages" not in body
        assert PUBLIC_V1_ROUTE in body


def test_readme_surfaces_compact_pilot_share_status_before_local_hygiene():
    readme = _read("README.md")

    assert "## Public Share Readiness" in readme
    assert "not currently published as a live hosted Streamlit app" in readme
    assert "FMP, Alpha Vantage, and Finnhub are optional local fallbacks" in readme
    assert "Coverage | Readiness-gated, not complete" in readme
    assert "Stock Research Command Center | Readiness-First Stock Research Workflow" in readme
    assert "## Pilot Share Status" in readme
    assert "Share as controlled portfolio/demo evidence under the root `LICENSE`" in readme
    assert "do not describe the repository as open source or reusable software" in readme
    assert "Generated CSV/JSON/report churn stays local unless an exact artifact is reviewed as evidence." in readme
    assert "`make project-status-check` -> `make provider-setup-checklist` -> a reviewed one-ticker smoke command" in readme
    assert "Use `make project-status` only when you intentionally want to refresh the dashboard-ready status snapshot." in readme
    assert "No broad coverage batch should run from setup alone." in readme
    assert "no public Streamlit URL is configured in this repository" in readme
    assert "`make linkedin-share-check` for the final LinkedIn Featured-card checklist" in readme
    assert readme.index("## Public Share Readiness") < readme.index("## Pilot Share Status")
    assert readme.index("## Pilot Share Status") < readme.index("## Local Data Hygiene")


def test_readme_has_compact_current_next_stages_for_external_reviewers():
    readme = _read("README.md")

    assert "## Current Next Stages" in readme
    assert "| LinkedIn publish | Ready after GitHub sync | If the branch is ahead, push reviewed commits after `make public-check`; if GitHub is synced, use the GitHub link and `docs/LINKEDIN_PROJECT_BRIEF.md`; do not claim hosted app availability. |" in readme
    assert "| Hosted Streamlit demo | External account required | Run `make hosted-demo-readiness`, then follow `docs/HOSTED_DEMO_DEPLOYMENT.md`; keep GitHub as the public link until the hosted route is verified. |" in readme
    assert "| FMP provider activation | External key required | Configure `FMP_API_KEY` outside the repo, then run one reviewed ticker smoke before any broader batch. |" in readme
    assert "| Peer readiness upgrade | Source-gated | Keep candidate peers as context only until source-backed peer rows pass review. |" in readme
    assert "| Optional earnings / estimates | Locked | Use trusted provider or reviewed manual rows only; do not infer optional context. |" in readme
    assert "| Broad proof queues | Do not retry now | Current queues are exhausted; reopen only after keyed provider rows, reviewed manual rows, or changed blockers exist. |" in readme
    assert "| Public UX polish | Share-review ready | Live desktop/mobile route notes are resolved; rerun `make public-ux-review-notes-check` after any UI wording, layout, or route change. |" in readme
    assert "| Generated artifacts | Excluded by default | Keep local CSV/report/sample-report churn unstaged unless one exact artifact is reviewed as public evidence. |" in readme
    assert "The next product stage is not another broad refresh loop" in readme
    assert "rerun live desktop/mobile review only after UI changes" in readme
    assert "choose a hosted app account only when you want a public URL" in readme
    assert readme.index("## Public Share Readiness") < readme.index("## Current Next Stages")
    assert readme.index("## Current Next Stages") < readme.index("## What You Can Analyze")


def test_hosted_demo_deployment_doc_keeps_hosting_optional_and_secret_safe():
    readme = _read("README.md")
    hosted = _read("docs/HOSTED_DEMO_DEPLOYMENT.md")
    requirements = _read("requirements.txt")
    secrets_template = _read(".streamlit/secrets.toml.example")
    checklist = _read("docs/PUBLIC_RELEASE_CHECKLIST.md")
    walkthrough = _read("docs/PUBLIC_DEMO_WALKTHROUGH.md")
    linkedin = _read("docs/LINKEDIN_PROJECT_BRIEF.md")

    assert "docs/HOSTED_DEMO_DEPLOYMENT.md" in checklist
    assert "docs/HOSTED_DEMO_DEPLOYMENT.md" in walkthrough
    assert "docs/HOSTED_DEMO_DEPLOYMENT.md" in linkedin
    assert "[Hosted Demo Deployment](docs/HOSTED_DEMO_DEPLOYMENT.md)" in readme

    assert "No public hosted Streamlit URL is configured in this repository." in hosted
    assert "A hosted app is optional" in hosted
    assert "GitHub is the public link until a deployment account is intentionally configured and verified." in hosted
    assert "Keep provider keys, account identifiers, tokens, and broker/session files outside the repo." in hosted
    assert "FMP_API_KEY" in hosted
    assert "ALPHA_VANTAGE_API_KEY" in hosted
    assert "FINNHUB_API_KEY" in hosted
    assert ".streamlit/secrets.toml.example" in hosted
    assert "do not commit `.streamlit/secrets.toml`" in hosted
    assert "Provider setup is not proof." in hosted
    assert "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History" in hosted
    assert "Set the hosted app entrypoint to `dashboard.py`" in hosted
    assert "The root `dashboard.py` file is a compatibility wrapper around `src.dashboard`" in hosted
    assert "Install dependencies from `requirements.txt` or `pyproject.toml`" in hosted
    assert "Keep `make dashboard` as the local verification path" in hosted
    assert "Use the GitHub repository link unless the hosted app exists" in hosted
    assert "## Link Decision Ladder" in hosted
    assert "| No hosted URL | GitHub repository link | `make hosted-demo-readiness` reports `external_account_required`; keep local `make dashboard` instructions. |" in hosted
    assert "| Hosted URL opens | Hosted app link can be considered | Open the public URL, confirm the five-page workflow starts in public mode, then rerun `make public-check` and `make browser-qa-evidence`. |" in hosted
    assert "| Provider keys added | Hosted app link plus source boundary note | Run `make provider-setup-checklist` and one reviewed provider smoke; setup alone does not prove coverage or unlock blocked inputs. |" in hosted
    assert "Do not replace the GitHub link with a hosted link until the hosted app opens successfully" in hosted
    assert "make hosted-demo-readiness" in hosted
    assert "stock picks" not in hosted.lower()
    assert "buy/sell" in hosted
    assert "streamlit>=1.44" in requirements
    assert "pandas>=2.2" in requirements
    assert "numpy>=1.26" in requirements
    assert "PyYAML>=6.0" in requirements
    assert "yfinance" not in requirements
    assert "ib-insync" not in requirements

    assert 'FMP_API_KEY = ""' in secrets_template
    assert 'ALPHA_VANTAGE_API_KEY = ""' in secrets_template
    assert 'FINNHUB_API_KEY = ""' in secrets_template
    assert 'IBKR_HOST = ""' in secrets_template
    assert 'IBKR_PORT = ""' in secrets_template
    assert 'IBKR_CLIENT_ID = ""' in secrets_template
    assert "Do not commit .streamlit/secrets.toml or real provider keys." in secrets_template


def test_public_docs_match_auto_price_ladder_order():
    readme = _read("README.md")
    strategy = _read("docs/DATA_STRATEGY.md")
    operator_guide = _read("docs/OPERATOR_GUIDE.md")
    roadmap = _read("ROADMAP.md")

    for doc in (readme, strategy, operator_guide, roadmap):
        assert "PROVIDER=auto" in doc
        assert "Stooq, Yahoo" in doc
        assert "optional IBKR read-only" in doc
        assert "FMP" in doc and "Alpha Vantage" in doc and "Finnhub" in doc
        assert "Yahoo, Stooq" not in doc


def test_readme_has_external_reviewer_handoff_before_operator_detail():
    readme = _read("README.md")
    checklist = _read("docs/PUBLIC_RELEASE_CHECKLIST.md")

    assert "## Two-Minute External Review Path" in readme
    assert "- GitHub-only review: start with the preview image, the five-page workflow map, and the `docs/PUBLIC_DEMO_WALKTHROUGH.md` script." in readme
    assert "- Live dashboard review: run `make dashboard`, open `http://localhost:8501/?mode=public`, then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History." in readme
    assert "- Evidence boundary: `docs/assets/linkedin-public-dashboard.png` and screenshots show product UI only; `make status-check TOP_N=5` remains the source for current local counts." in readme
    assert "- Share boundary: controlled portfolio/demo evidence only, not open-source reuse, investment advice, broker integration, or data-freshness proof." in readme
    assert "## External Reviewer Handoff" in readme
    assert "| Review first | Dashboard preview, then Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History. |" in readme
    assert "| Skip unless operating locally | Broad CSV/report churn, provider setup, validate/preview/apply commands, and raw proof ledgers. |" in readme
    assert "| Do not claim | Screenshots prove data freshness, blocked inputs are ready, the repo is open source, or the product gives buy/sell instructions. |" in readme
    assert "| Best next question | Can a reviewer understand what is ready, blocked, excluded, and proof-backed before opening advanced details? |" in readme
    assert readme.index("## Two-Minute External Review Path") < readme.index("## External Reviewer Handoff")
    assert readme.index("## External Reviewer Handoff") < readme.index("## Data Coverage Strategy")
    assert "Keep the guided product flow near the top" in checklist
    assert "then `make dashboard`, then the Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History path" in checklist
    assert "Keep terminal proof commands secondary" in checklist
    assert "Put the best demo commands near the top" not in checklist


def test_public_docs_share_same_coverage_gate_rule():
    readme = _read("README.md")
    checklist = _read("docs/PUBLIC_RELEASE_CHECKLIST.md")
    runbook = _read("docs/PILOT_RUNBOOK.md")

    for doc in (readme, checklist, runbook):
        assert "No broad coverage batch should run from setup alone" in doc
        assert "Provider setup is only an activation boundary" in doc
        assert "it can activate a source" in doc
        assert "readiness changes still require validate, preview, rejected-row review" in doc
        assert "Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist" in doc
    assert "run only the listed reviewed one-ticker smoke command before any broader batch" in checklist
    audit = _read("docs/PILOT_READINESS_AUDIT.md")
    assert "reviewed one-ticker smoke command" in audit
    assert "provider smoke command" not in audit


def test_methodology_doc_surfaces_version_freshness_provenance_and_limits():
    methodology = _read("docs/METHODOLOGY.md")

    assert "## Methodology Status" in methodology
    assert "Methodology v1 - readiness-first deterministic gates" in methodology
    assert "## Public Workflow Boundary" in methodology
    assert PUBLIC_V1_ROUTE in methodology
    assert "The public page order is a reading workflow, not an analysis shortcut." in methodology
    assert "Home starts with the visitor question, next safe action, and stop rule before readiness counts." in methodology
    assert "latest price date, latest fundamentals filing date, peer review date, optional-context review date, and proof-ledger date" in methodology.lower()
    assert "Source, as-of date, reviewed/import status" in methodology
    assert "WACC, terminal growth, forecast years, growth caps, FCF margin caps" in methodology
    assert "Candidate peers can guide review, but they are not trusted peer proof." in methodology
    assert "not a complete valuation terminal, not investment advice, and not a recommendation engine" in methodology
    assert "They do not unlock blocked inputs or prove today's market/fundamental data." in methodology


def test_pilot_readiness_audit_does_not_overstate_github_sync():
    audit = _read("docs/PILOT_READINESS_AUDIT.md")
    lowered = audit.lower()

    assert "rerun the live status gate before sharing" in lowered
    assert "local reviewed commits may be ahead of github until pushed" in lowered
    assert "generated csv/report churn" in lowered
    assert "reviewed local commits still need push" not in lowered
    assert "Current branch is synced with origin" not in audit
    assert not re.search(r"\bahead \d+\b", audit)


def test_public_walkthrough_uses_stock_selector_before_single_stock_report():
    walkthrough = _read("docs/PUBLIC_DEMO_WALKTHROUGH.md")

    assert "## Share Boundary" in walkthrough
    assert "Screenshots are product evidence only; they do not prove data freshness or unlock blocked inputs." in walkthrough
    assert "Use `make status-check TOP_N=5` for current coverage and blocker counts." in walkthrough
    assert "controlled portfolio/demo license" in walkthrough
    assert PUBLIC_V1_ROUTE in walkthrough
    assert "Stock Selector" in walkthrough
    assert "Proof History" in walkthrough
    assert "Data Health source-proof lane" not in walkthrough
    assert "Home readiness snapshot ->" not in walkthrough
    assert "Home readiness snapshot -> Single-Stock Report -> Data Health source-proof lane -> proof history" not in walkthrough


def test_external_review_story_is_consistent_across_public_docs():
    readme = _read("README.md")
    walkthrough = _read("docs/PUBLIC_DEMO_WALKTHROUGH.md")
    linkedin = _read("docs/LINKEDIN_PROJECT_BRIEF.md")

    assert "## Two-Minute External Review Path" in readme
    assert "## Two-Minute External Review Path" in walkthrough
    assert "Two-minute external review path:" in linkedin
    for doc in (readme, walkthrough, linkedin):
        assert "GitHub-only review" in doc
        assert "Live dashboard review" in doc
        assert PUBLIC_V1_ROUTE in doc
        assert "screenshots show product UI only" in doc
        assert "make status-check TOP_N=5" in doc
        assert "controlled portfolio/demo" in doc
        assert "data-freshness proof" in doc
        assert "open-source reuse" in doc
    assert walkthrough.index("## Two-Minute External Review Path") < walkthrough.index("## Demo Examples")


def test_public_release_checklist_names_v1_routes_and_primary_surfaces():
    checklist = _read("docs/PUBLIC_RELEASE_CHECKLIST.md")

    for route in (
        "?mode=public&page=home",
        "?mode=public&page=stock-selector",
        "?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        "?mode=public&page=data-health",
        "?mode=public&page=proof-history",
    ):
        assert route in checklist

    assert "Stock Selector is the primary public stock-selection surface" in checklist
    assert "Proof History evidence is the public proof-inspection surface" in checklist
    assert "Data Health should stay the first coverage-readiness surface" in checklist
    assert "one answer per lane before queue drawers, route maps, advanced evidence details, or proof ledgers" in checklist
    assert "one answer per lane before queue drawers, route maps, raw tables, or proof ledgers" not in checklist
    assert "Operator context" in checklist
    assert "`make public-check` now includes `make license-status`" in checklist
    assert "license/reuse boundary is checked in the same share gate" in checklist
    assert "`make linkedin-share-check` for the final LinkedIn Featured-card checklist" in checklist
    assert "it does not open LinkedIn, upload files, edit your profile, refresh data, stage files, commit, or push" in checklist


def test_dashboard_qa_tracks_v1_replacement_browser_checks():
    qa = _read("docs/DASHBOARD_QA.md")

    assert "V1 Public UI Replacement QA" in qa
    assert "stock-selector" in qa
    assert "single-stock-report&ticker=NVDA&open=1" in qa
    assert "proof-history" in qa
    assert "no visible first-viewport raw dataframe" in qa
    assert "`make browser-qa-evidence` is the deterministic share gate" in qa
    assert "`make public-check` is the current end-to-end public gate" in qa
    assert "`make public-ux-review-checklist` is the copy-only normal-browser checklist" in qa
    assert "`make project-status-check` is the no-write status read for review loops" in qa
    assert "dashboard smoke, browser QA evidence" in qa
    assert "normal-browser desktop/mobile pass" in qa
    assert "Treat in-app browser capture timeouts as environment-limited" in qa
    assert "raw-table-first view" in qa
    assert "the current in-app browser shows `localhost refused to connect`" not in qa


def test_public_demo_and_linkedin_copy_use_v1_route_sequence():
    makefile = _read("Makefile")
    brief = _read("docs/LINKEDIN_PROJECT_BRIEF.md")

    assert PUBLIC_V1_ROUTE in makefile
    assert PUBLIC_V1_ROUTE in brief
    assert "no public hosted Streamlit URL is configured yet" in brief
    assert "Coverage boundary" in brief
    assert "Provider boundary" in brief
    assert "GitHub demo with real product screenshots and local run instructions" in brief
    assert "provider-key activation" in brief
    assert "readiness-backed selection comes first" in makefile
    assert "Review one stock, Improve data coverage, and Inspect proof" not in makefile
    assert "Check data coverage:     make readiness-ops-center" in makefile
    assert "make linkedin-share-check" in makefile
    assert "GitHub's generated OpenGraph card" in makefile
