from pathlib import Path
import re


PUBLIC_V1_ROUTE = (
    "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History"
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_product_tour_matches_v1_public_route_model():
    readme = _read("README.md")

    assert "## External Reviewer Start Here" in readme
    assert "This repository is ready to review as a controlled GitHub/LinkedIn portfolio demo." in readme
    assert "It is not currently published as a hosted Streamlit app." in readme
    assert "| What is the live app path? | Run `make demo-dashboard`, then open `http://localhost:8501/?mode=public`. |" in readme
    assert "[Data Profiles](docs/DATA_PROFILES.md)" in readme
    assert "| What workflow should I follow? | Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History. |" in readme
    assert "| What should I run when I ask what is next? | Run `make next-stage` for the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder; it is read-only and does not refresh data, import rows, stage files, commit, push, deploy, or expose secrets. |" in readme
    assert "| What should I not claim? | No hosted app yet, no open-source reuse, no investment advice, no broker integration, no auto-trading, and no screenshot-based data freshness proof. |" in readme
    assert "First review move: open Stock Selector" in readme
    assert "screenshots are product evidence only" in readme
    assert "| What proves current local readiness? | `make status-check TOP_N=5` remains the source for current local counts; screenshots are product evidence only. |" in readme
    assert "The controlled Public workspace keeps its existing five-page path" in readme
    assert "| Home |" in readme
    assert "| Stock Selector |" in readme
    assert "| Single-Stock Report |" in readme
    assert "| Data Health |" in readme
    assert "| Proof History |" in readme
    assert "| Stock Selector | You want to filter readiness-backed candidates" in readme
    assert "| Proof History | You want one evidence answer before opening raw proof ledger details." in readme
    assert "| Proof History | You want to see the proof ledger" not in readme
    assert "| Proof History |" in readme and "| `Proof History` |" in readme
    assert PUBLIC_V1_ROUTE in readme
    assert "Data Health source-proof lane" not in readme
    assert "Proof History is the public proof-inspection surface" not in readme
    assert "Operator context" in readme
    assert "Home readiness snapshot ->" not in readme
    assert "Home readiness snapshot -> Single-Stock Report -> Data Health source-proof lane -> proof history" not in readme
    assert "Start with the three paths" not in readme


def test_readme_and_roadmap_keep_active_planning_separate_from_completed_history():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    completed = _read("docs/COMPLETED_MILESTONES.md")

    assert "Pilot packaging is read-only first" in readme
    assert "make pilot-share-brief" in readme
    assert "does not refresh data or unlock blocked inputs" in readme
    assert "Provider setup is only an activation boundary" in readme

    assert "## Now" in roadmap
    assert "## Next" in roadmap
    assert "## Later" in roadmap
    assert "## Dependencies And Manual Gates" in roadmap
    assert "## Success Gates" in roadmap
    assert "## Completed Milestones" not in roadmap
    assert "docs/COMPLETED_MILESTONES.md" in roadmap
    assert "Pilot Operator Runbook V1" in completed
    assert "share gate, source gate, provider setup, reviewed one-ticker smoke command, validate/preview, packet, and hygiene" in completed
    assert "without reopening broad proof loops" in completed


def test_roadmap_current_counts_are_live_command_gated():
    roadmap = _read("ROADMAP.md")

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

    assert "## External Reviewer Start Here" in readme
    assert "not currently published as a hosted Streamlit app" in readme
    assert "No hosted app yet, no open-source reuse, no investment advice, no broker integration, no auto-trading, and no screenshot-based data freshness proof." in readme
    assert "## Pilot Share Status" in readme
    assert "Share as controlled portfolio/demo evidence under the root `LICENSE`" in readme
    assert "do not describe the repository as open source or reusable software" in readme
    assert "Generated CSV/JSON/report churn stays local unless an exact artifact is reviewed as evidence." in readme
    assert "`make project-status-check` -> `make provider-setup-checklist` -> a reviewed one-ticker smoke command" in readme
    assert "Use `make project-status` only when you intentionally want to refresh the dashboard-ready status snapshot." in readme
    assert "No broad coverage batch should run from setup alone." in readme
    assert "no public Streamlit URL is configured in this repository" in readme
    assert "`make linkedin-share-check` for the final LinkedIn Featured-card checklist" in readme
    assert readme.index("## External Reviewer Start Here") < readme.index("## Pilot Share Status")
    assert readme.index("## Pilot Share Status") < readme.index("## Local Data Hygiene")


def test_readme_has_compact_current_next_stages_for_external_reviewers():
    readme = _read("README.md")

    assert "## Personal Research Start Here" in readme
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in readme
    assert "Public remains the controlled demo" in readme
    assert "Data Health and Proof History stay under **Advanced Evidence**" in readme
    assert "## Now / Next / Not Yet" in readme
    assert "| Now | GitHub/LinkedIn portfolio demo with public workflow, screenshots, methodology, local run commands, manual gates, and a locally passed performance gate. | Use `make public-check` before sharing; keep generated churn excluded and do not treat local timing as hosted proof. |" in readme
    assert "| Next | Optional controlled hosted preview and task-based external pilot review. | Hosting remains external until a URL is verified; reviewer feedback must remain anonymous workflow evidence, not investment opinion. |" in readme
    assert "| Not yet | Full hosted data product, complete fundamentals/peer/optional coverage, or provider-backed automation across the universe. | Do not claim this until external hosting, provider keys, source proof, validation, preview, apply, rebuilt readiness, and proof history support it. |" in readme
    assert "This is the fastest reviewer answer: the product is shareable as a controlled demo now, deeper coverage is source-gated, and hosting/provider automation stays optional until verified." in readme
    assert "The local fixed-demo performance gate has passed and remains a regression check" in readme
    assert "The active evidence stage is a narrow, append-only Earnings Nowcast pilot" in readme
    assert "hosting and external review remain separate external stages" in readme
    assert readme.index("## Personal Research Start Here") < readme.index("## External Reviewer Start Here")
    assert readme.index("## External Reviewer Start Here") < readme.index("## Now / Next / Not Yet")
    assert readme.index("## Now / Next / Not Yet") < readme.index("## What You Can Analyze")


def test_public_status_language_keeps_share_review_ready_local_only():
    readme = _read("README.md")

    assert "This repository is ready to review as a controlled GitHub/LinkedIn portfolio demo." in readme
    assert "It is not currently published as a hosted Streamlit app." in readme
    assert "Hosting remains external until a URL is verified" in readme
    assert "make public-performance-gate" in readme


def test_active_roadmap_puts_performance_before_hosting_and_external_pilot():
    roadmap = _read("ROADMAP.md")

    performance = roadmap.index("### P0: Performance Release Candidate")
    hosted = roadmap.index("### P1: Controlled Hosted Preview Verification")
    pilot = roadmap.index("### P1: Controlled Pilot Review")

    assert performance < hosted < pilot
    assert "data/demo/manifest.json" in roadmap
    assert "first useful" in roadmap.lower()
    assert "p90" in roadmap.lower()


def test_methodology_defines_lane_level_freshness_policy_without_claiming_live_data():
    methodology = _read("docs/METHODOLOGY.md")

    assert "## Lane-Level Freshness Policy" in methodology
    for lane in (
        "Price / momentum",
        "Fundamentals",
        "Share count",
        "DCF",
        "Trusted peers",
        "Earnings / estimates",
    ):
        assert f"| {lane} |" in methodology
    assert "current" in methodology
    assert "review_due" in methodology
    assert "stale_or_unknown" in methodology
    assert "A timestamp cannot turn an unsupported row into trusted evidence" in methodology


def test_public_docs_keep_nowcast_probability_withheld_until_calibrated():
    text = _read("docs/EARNINGS_NOWCAST_PILOT.md")

    assert "baseline_ready" in text
    assert "signal_context_ready" in text
    assert "backtest_ready" in text
    assert "calibrated" in text
    assert "No numerical Beat/Miss probability is shown before calibration" in text
    assert "does not predict post-earnings price movement" in text
    assert "synthetic test evidence only" in text
    assert "awaiting_point_in_time_consensus" in text
    assert "awaiting_calibration_evidence" in text


def test_roadmap_and_readme_describe_nowcast_infrastructure_without_claiming_real_coverage():
    roadmap = _read("ROADMAP.md")
    readme = _read("README.md")

    assert "Earnings Nowcast real-data safety infrastructure" in roadmap
    assert "Real semiconductor nowcast coverage remains `awaiting_point_in_time_consensus`" in roadmap
    assert "Earnings Nowcast Pilot" in readme
    assert "deterministic synthetic-fixture workflow" in readme
    assert "does not establish real-company coverage or predictive accuracy" in readme


def test_product_direction_decision_stays_provisional_until_external_evidence_exists():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    decision = _read("docs/PRODUCT_DIRECTION_DECISION.md")

    assert "[Product Direction Decision](docs/PRODUCT_DIRECTION_DECISION.md)" in readme
    assert "docs/PRODUCT_DIRECTION_DECISION.md" in roadmap
    for path in (
        "Portfolio-quality research prototype",
        "Maintained research tool",
        "Operated research platform",
    ):
        assert path in decision
    for criterion in (
        "Reviewer demand",
        "Operating burden",
        "Data licensing",
        "Provider reliability",
        "Monitoring and support",
    ):
        assert criterion in decision
    assert "Current decision: provisional" in decision
    assert "awaiting_external_review" in decision
    assert "external_account_required" in decision
    assert "Do not infer demand" in decision


def test_linkedin_brief_has_now_next_not_yet_share_framing():
    linkedin = _read("docs/LINKEDIN_PROJECT_BRIEF.md")

    assert "## Now / Next / Not Yet" in linkedin
    assert "| Now | GitHub/LinkedIn portfolio demo with the guided public workflow, screenshots, methodology, and local run commands. | Share the GitHub link and curated screenshot after GitHub is synced and `make public-check` passes. |" in linkedin
    assert "| Next | Source-backed Earnings Nowcast evidence pilot, plus optional hosted preview and controlled review. | Keep synthetic fixtures separate from real evidence; do not imply a hosted URL, private access, predictive validation, or provider-backed automation before verification. |" in linkedin
    assert "| Not yet | Full hosted data product, complete fundamentals/peer/optional coverage, or provider-backed automation across the universe. | Do not claim complete coverage, data freshness proof, or automated provider-backed readiness. |" in linkedin
    assert "Use this framing when someone asks whether the project is ready: it is ready to review as a controlled portfolio demo, while hosting and deeper coverage remain verified next stages." in linkedin
    assert "If someone asks what to do next, run `make next-stage` before opening operator proof queues; it prints the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder without refreshing data, importing rows, staging files, pushing, deploying, or exposing secrets." in linkedin
    assert linkedin.index("make next-stage") < linkedin.index("Run `make project-status-check` first")


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
    assert "config/hosted_demo.env.example" in hosted
    assert "HOSTED_DEMO_URL" in hosted
    assert "config/hosted_demo.env" in hosted
    assert "Hosted platforms can provide `HOSTED_DEMO_URL` directly as an environment variable; local operators can use the ignored `config/hosted_demo.env` marker for the same readiness check." in hosted
    assert "A configured hosted URL is still a manual verification gate" in hosted
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
    assert "Keep `make demo-dashboard` as the public-profile verification path" in hosted
    assert "## Hosted Setup Values" in hosted
    assert "| Repository | `YuzeJ21/Stock-Analysis` | Use the same GitHub repo link that is shared in LinkedIn until the hosted URL is verified. |" in hosted
    assert "| Branch | `main` | Deploy only reviewed commits that already passed public gates locally. |" in hosted
    assert "| Main file path | `dashboard.py` | Root compatibility wrapper for `src.dashboard`; do not point hosting at generated reports. |" in hosted
    assert "| Dependency file | `requirements.txt` | Hosted baseline only; optional providers stay behind secrets and smoke tests. |" in hosted
    assert "| Public route | `/?mode=public` | First hosted view must start in public visitor mode, not operator mode. |" in hosted
    assert "| Public-profile health check | `make demo-dashboard-smoke` | Keep the compact public profile green before debugging hosting-specific behavior. |" in hosted
    assert "## Post-Deploy Smoke Checklist" in hosted
    assert "Open the hosted root URL and confirm it lands on `/?mode=public` or visibly offers Public visitor mode first." in hosted
    assert "Open `/?mode=public&page=single-stock-report&ticker=NVDA&open=1` and confirm the selected-ticker answer appears before detailed report tables." in hosted
    assert "Open `/?mode=public&page=data-health` and confirm the coverage answer appears before provider setup, commands, or raw proof ledgers." in hosted
    assert "Open `/?mode=public&page=proof-history` and confirm proof history is evidence-only before raw ledger details." in hosted
    assert "Use the GitHub repository link unless the hosted app exists" in hosted
    assert "## Link Decision Ladder" in hosted
    assert "| No hosted URL | GitHub repository link | `make hosted-demo-readiness` reports `external_account_required`; keep `make demo-dashboard` instructions. |" in hosted
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

    assert "## External Reviewer Start Here" in readme
    assert "| What should I open first? | Start with this README preview, then use `docs/PUBLIC_DEMO_WALKTHROUGH.md` for the five-page workflow. |" in readme
    assert "| What is the live app path? | Run `make demo-dashboard`, then open `http://localhost:8501/?mode=public`. |" in readme
    assert "| What proves current local readiness? | `make status-check TOP_N=5` remains the source for current local counts; screenshots are product evidence only. |" in readme
    assert "| What should I not claim? | No hosted app yet, no open-source reuse, no investment advice, no broker integration, no auto-trading, and no screenshot-based data freshness proof. |" in readme
    assert "## External Reviewer Handoff" in readme
    assert "| Review first | Dashboard preview, then Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History. |" in readme
    assert "| Skip unless operating locally | Broad CSV/report churn, provider setup, validate/preview/apply commands, and raw proof ledgers. |" in readme
    assert "| Do not claim | Screenshots prove data freshness, blocked inputs are ready, the repo is open source, or the product gives buy/sell instructions. |" in readme
    assert "| Best next question | Can a reviewer understand what is ready, blocked, excluded, and proof-backed before opening advanced details? |" in readme
    assert readme.index("## External Reviewer Start Here") < readme.index("## External Reviewer Handoff")
    assert readme.index("## External Reviewer Handoff") < readme.index("## Data Coverage Strategy")
    assert "Confirm `README.md` starts with `External Reviewer Start Here`" in checklist
    assert "then `make dashboard` and the Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History path" in checklist
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

    assert "Last repo-truth refresh: 2026-07-09" in audit
    assert "Current stage: controlled GitHub/LinkedIn pilot-share package with manual gates." in audit
    assert "Hosted demo remains external-account-required until a public URL is deployed and verified." in audit
    assert "Provider activation remains external-key-required for FMP, Alpha Vantage, and Finnhub." in audit
    assert "trusted-data pilot, ready to enter" not in audit
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
    assert "Run `make next-stage` when you want the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder; it is read-only and does not refresh data, import rows, stage files, push, deploy, or expose secrets." in walkthrough
    assert "make next-stage                  # print the current package/provider/hosted/source-queue ladder without changing local data" in walkthrough
    best_path = walkthrough.split("Best visitor path:", 1)[1].split("What each page answers:", 1)[0]
    assert best_path.index("make demo") < best_path.index("make next-stage")
    assert best_path.index("make next-stage") < best_path.index("make status-check TOP_N=5")
    assert "Stock Selector" in walkthrough
    assert "Proof History" in walkthrough
    assert "Data Health source-proof lane" not in walkthrough
    assert "Home readiness snapshot ->" not in walkthrough
    assert "Home readiness snapshot -> Single-Stock Report -> Data Health source-proof lane -> proof history" not in walkthrough


def test_external_review_story_is_consistent_across_public_docs():
    readme = _read("README.md")
    walkthrough = _read("docs/PUBLIC_DEMO_WALKTHROUGH.md")
    linkedin = _read("docs/LINKEDIN_PROJECT_BRIEF.md")

    assert "## External Reviewer Start Here" in readme
    assert "## Two-Minute External Review Path" in walkthrough
    assert "Two-minute external review path:" in linkedin
    assert "What should I open first?" in readme
    assert "What is the live app path?" in readme
    for doc in (walkthrough, linkedin):
        assert "GitHub-only review" in doc
        assert "Live dashboard review" in doc
    for doc in (readme, walkthrough, linkedin):
        assert PUBLIC_V1_ROUTE in doc
        assert "screenshots show product UI only" in doc or "screenshots are product evidence only" in doc
        assert "make status-check TOP_N=5" in doc
        assert "controlled portfolio/demo" in doc
        assert "data-freshness proof" in doc or "data freshness proof" in doc
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


def test_dashboard_qa_records_commercial_beta_research_mode_live_review():
    qa = _read("docs/DASHBOARD_QA.md")

    assert "Commercial Beta Research Workflow Live Review" in qa
    assert "1280x720" in qa
    assert "390x844" in qa
    assert "Research Desk, Discover, Company Workbench, and Monitor" in qa
    assert "ArrowInvalid" in qa
    assert "no horizontal overflow" in qa
    assert "product evidence only" in qa


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
    assert "make next-stage                 Print the current next-stage decision ladder" in makefile
    assert "make project-status-check       Read current coverage, blockers, and executable next steps" in makefile
    assert "Check current counts:    make status-check TOP_N=5" in makefile
    assert "make linkedin-share-check" in makefile
    assert "GitHub's generated OpenGraph card" in makefile


def test_active_roadmap_and_price_history_maintenance_are_finite_and_read_only():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    next_stage = _read("docs/NEXT_STAGE_ROADMAP.md")
    continuity = _read("docs/COVERAGE_CONTINUITY_GOAL_PROMPT.md")

    assert "The active roadmap is ROADMAP.md" in next_stage
    assert "The active roadmap is ROADMAP.md" in continuity
    assert "make project-status-check" in next_stage
    assert "make readiness-ops-center" in next_stage
    assert "make price-history-proof-queue TOP_N=25" in next_stage
    assert "make price-history-batch-closeout TOP_N=25" in next_stage
    assert "momentum-not-ready" in roadmap
    assert "unreviewed preferred-history candidates" in roadmap
    assert "reviewed source-limited items" in roadmap
    assert "INCLUDE_REVIEWED=1" in roadmap
    assert "make price-history-batch-closeout TOP_N=25" in roadmap
    assert "stop on no readiness movement in reviewed scope" in roadmap
    assert "no identical source-limit retry unless source behavior or verified OHLCV changes" in roadmap
    assert "batch compatible proof evidence intentionally" in roadmap
    assert "never commit or push one proof row per ticker by default" in roadmap
    assert "pivot to the next roadmap item when no executable candidates" in roadmap
    assert "make price-history-proof-queue TOP_N=25" in readme
    assert "make price-history-batch-closeout TOP_N=25" in readme
    assert "read-only batch closeout" in readme


def test_thesis_journal_docs_preserve_append_only_research_boundary():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    operator = _read("docs/OPERATOR_GUIDE.md")

    assert "append-only Research Thesis Journal" in readme
    assert "P0: Research Thesis And Evidence Journal" in roadmap
    assert "P2: Scenario Lab" in roadmap
    assert "generated thesis text is context only" in methodology
    assert "never creates or revises a journal entry" in methodology
    assert "data/research_thesis_journal.csv" in provenance
    assert "supersedes_entry_id" in provenance
    assert "make thesis-journal TICKER=NVDA" in operator
    assert "CONFIRM_REVIEWED=1 make thesis-journal-record" in operator


def test_scenario_lab_docs_define_session_local_readiness_gated_boundary():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")

    assert "session-local Scenario Lab" in readme
    assert "P2: Scenario Lab - Implemented" in roadmap
    assert "revenue growth from -50% to 40%" in methodology
    assert "terminal growth must remain below WACC" in methodology
    assert "Scenario Lab never writes canonical data" in provenance
    assert "blocked or excluded" in provenance


def test_source_freshness_timeline_docs_preserve_timestamp_truth():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")

    assert "Source Freshness Timeline" in readme
    assert "Source Freshness Timeline - Implemented" in roadmap
    assert "never substitutes retrieval time" in methodology
    assert "Source Freshness Timeline Contract" in provenance
    assert "missing timestamp" in provenance


def test_research_comparison_docs_preserve_non_ranking_boundary():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")

    assert "Research Comparison View" in readme
    assert "Research Comparison View - Implemented" in roadmap
    assert "two or three selected tickers" in methodology
    assert "never calculates a score or winner" in methodology
    assert "Research Comparison Contract" in provenance
    assert "candidate peer context cannot satisfy trusted-peer readiness" in provenance
