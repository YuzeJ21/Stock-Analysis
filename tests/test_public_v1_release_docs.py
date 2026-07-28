from pathlib import Path
import re


PUBLIC_V1_ROUTE = (
    "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History"
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_proof_readiness_reconciliation_docs_keep_historical_proof_separate_from_current_state():
    roadmap = _read("ROADMAP.md")
    operator = _read("docs/OPERATOR_GUIDE.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, operator, prompt):
        assert "make proof-readiness-reconciliation TOP_N=20" in text
        assert "historical_supported_currently_blocked" in text
        assert "current saved readiness remains authoritative" in text.lower()
        assert "explicit_ticker_change" in text
        assert "current_canonical_row_missing" in text
        assert "does not establish the historical cause" in text.lower()
    assert "current-snapshot audit" in roadmap.lower()
    assert "does not restore canonical data" in operator.lower()
    assert "before reusing a supporting proof outcome" in prompt.lower()
    assert "source rights" in prompt.lower()
    assert "field scope" in prompt.lower()
    assert "changed_tickers" in operator
    assert "changed_tickers" in prompt
    assert "structured per-ticker" in prompt.lower()
    assert "future" in roadmap.lower()


def test_provider_neutral_workspace_authorization_is_documented_without_hosted_claims():
    architecture = _read("docs/PRIVATE_BETA_ARCHITECTURE.md")
    roadmap = _read("ROADMAP.md")
    continuation = _read(
        "docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md"
    )

    for document in (architecture, roadmap, continuation):
        normalized = " ".join(document.split())
        assert "provider-neutral" in normalized
        assert "deny-by-default" in normalized
        assert "append-only" in normalized
        assert "privacy-safe audit obligation" in normalized
        assert "does not prove hosted authentication" in normalized

    assert "src.hosted_access_control.evaluate_workspace_access" in architecture
    normalized_architecture = " ".join(architecture.split())
    assert (
        "The evaluator performs no authentication, persistence, audit storage, "
        "retention, monitoring" in normalized_architecture
    )
    assert (
        "rollback, incident response, or operated capacity. All such states "
        "remain external" in normalized_architecture
    )

    normalized_roadmap = " ".join(roadmap.split())
    assert (
        "**Exit gate:** the actual hosted environment directly proves every "
        "claimed control, including an observed rollback rehearsal and named "
        "owner." in normalized_roadmap
    )
    assert (
        "The module has no dashboard, ledger, readiness, provider, persistence, "
        "environment, network, or generated-artifact integration."
        in normalized_roadmap
    )
    assert (
        "does not prove hosted authentication, deployed isolation, audit storage, "
        "retention, monitoring, rollback, incident response, operated capacity"
        in normalized_roadmap
    )

    normalized_continuation = " ".join(continuation.split())
    assert "Do not create or change hosted accounts" in continuation
    assert (
        "does not prove hosted authentication, deployed isolation, persistence, "
        "audit storage, retention, monitoring, rollback, incident response, "
        "operated capacity" in normalized_continuation
    )
    assert (
        "Provider-specific integration remains blocked until the exact identity, "
        "storage, logging, host, and operating environment are explicitly approved."
        in normalized_continuation
    )


def test_two_company_cash_preview_docs_preserve_bounded_portability_boundary():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (methodology, provenance, personal, roadmap, prompt):
        assert "AMD Q1 FY2026" in text
        assert "0000002488-26-000076" in text
        assert "bounded two-company portability" in text.lower()
    assert "cash_preview=1" in personal
    assert "production_activation=false" in provenance
    assert "readiness_promotions=()" in provenance
    assert "does not prove broad company coverage" in roadmap.lower()
    assert "do not add a third company" in prompt.lower()


def test_makefile_exposes_stdout_only_readiness_preview_contract():
    makefile = _read("Makefile")

    assert "readiness-preview" in makefile.splitlines()[0]
    assert (
        "make readiness-preview [TOP_N=20] Preview stable readiness impact, change causes, and promotion evidence in memory without writing files"
        in makefile
    )
    assert (
        "readiness-preview:\n\t@PYTHONDONTWRITEBYTECODE=1 python3 -m src.readiness_preview --top-n $(or $(TOP_N),20)"
        in makefile
    )


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


def test_active_roadmap_is_a_concise_current_decision_index():
    roadmap = _read("ROADMAP.md")

    for heading in (
        "## Now",
        "## Next",
        "## Externally blocked",
        "## Later",
        "## Completed with evidence",
    ):
        assert heading in roadmap
    assert len(roadmap.splitlines()) <= 320


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

    assert readme.count("## External Reviewer Start Here") == 1
    assert "## Personal Research Start Here" not in readme
    assert "Primary product workflow" in readme
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in readme
    assert "Secondary controlled demo" in readme
    assert "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History" in readme
    assert "Data Health and Proof History stay under **Advanced Evidence**" in readme
    assert "## Now / Next / Not Yet" in readme
    assert "| Now | GitHub/LinkedIn portfolio demo with public workflow, screenshots, methodology, local run commands, manual gates, and a locally passed performance gate. | Use `make public-check` before sharing; keep generated churn excluded and do not treat local timing as hosted proof. |" in readme
    assert "| Next | Optional controlled hosted preview and task-based external pilot review. | Hosting remains external until a URL is verified; reviewer feedback must remain anonymous workflow evidence, not investment opinion. |" in readme
    assert "| Not yet | Full hosted data product, complete fundamentals/peer/optional coverage, or provider-backed automation across the universe. | Do not claim this until external hosting, provider keys, source proof, validation, preview, apply, rebuilt readiness, and proof history support it. |" in readme
    assert "This is the fastest reviewer answer: the product is shareable as a controlled demo now, deeper coverage is source-gated, and hosting/provider automation stays optional until verified." in readme
    assert "local Commercial Research Beta foundation" in readme
    assert "not a hosted or commercially launched product" in readme
    assert "Authentication, private workspaces, operated data rights, real beta users, and repeatable provider operations remain separate gates" in readme
    assert readme.index("## External Reviewer Start Here") < readme.index("## Now / Next / Not Yet")
    assert readme.index("## Now / Next / Not Yet") < readme.index("## What You Can Analyze")


def test_public_status_language_keeps_share_review_ready_local_only():
    readme = _read("README.md")

    assert "This repository is ready to review as a controlled GitHub/LinkedIn portfolio demo." in readme
    assert "It is not currently published as a hosted Streamlit app." in readme
    assert "Hosting remains external until a URL is verified" in readme
    assert "make public-performance-gate" in readme


def test_active_roadmap_keeps_completed_performance_separate_from_external_gates():
    roadmap = _read("ROADMAP.md")

    completed = roadmap.index("## Completed with evidence")
    performance = roadmap.index("### P0: Performance Release Candidate")
    assert roadmap.index("## Externally blocked") < completed < performance
    assert "`hosted_account_and_controls_required`" in roadmap
    assert "`independent_reviewers_required`" in roadmap
    assert "data/demo/manifest.json" in roadmap
    assert "first useful" in roadmap.lower()
    assert "p90" in roadmap.lower()
    assert "make commercial-beta-release-check" in roadmap
    assert "make commercial-beta-performance-gate" in roadmap


def test_performance_release_gate_records_immutable_research_evidence():
    performance = _read("docs/PERFORMANCE_RELEASE_GATE.md")

    assert "immutable release-candidate" in performance
    assert re.search(r"commit `[0-9a-f]{40}`", performance)
    assert "48 recorded route samples, zero failures, and no horizontal overflow" in performance
    for route in ("Research Desk", "Discover", "Company Workbench", "Monitor"):
        assert f"| {route} | 1280x720 |" in performance
        assert f"| {route} | 390x844 |" in performance
    assert "/tmp/stock-command-center-commercial-beta-performance.json" in performance
    assert "Keep it out of\nGit" in performance


def test_hosted_handoff_covers_research_routes_health_and_rollback_without_claiming_a_host():
    hosted = _read("docs/HOSTED_DEMO_DEPLOYMENT.md")

    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in hosted
    assert "make commercial-beta-performance-gate BASE_URL=<verified-url>" in hosted
    assert "## Health Check And Rollback" in hosted
    assert "external_account_required" in hosted
    assert "Do not claim private or authenticated access" in hosted


def test_private_beta_architecture_keeps_operating_controls_external_and_independent():
    architecture = _read("docs/PRIVATE_BETA_ARCHITECTURE.md")

    assert "external_operations_required" in architecture
    assert "incident response" in architecture
    assert "rollback" in architecture
    assert "owner capacity" in architecture
    assert "authentication, workspaces, user data separation" in architecture
    assert "A local runbook does not prove" in architecture


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

    assert "Stock Research Command Center | Evidence-First Company Research" in linkedin
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in linkedin
    assert "stable GitHub repository link only after this reviewed feature reaches the default branch" in linkedin
    assert "Draft engineering preview" in linkedin
    assert "readiness counts" not in linkedin.lower()
    assert "Workbench answer-first screenshot" in linkedin
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
    assert "then Research Desk -> Discover -> Company Workbench -> Monitor" in checklist
    assert "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History as the secondary controlled Public demo" in checklist
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
    assert "Stock Research Command Center | Evidence-First Company Research" in makefile
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in makefile
    assert "stable GitHub repository link only after this reviewed feature reaches the default branch" in makefile
    assert "Draft engineering preview" in makefile
    assert "count-safe Company Workbench answer visual" in makefile
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
    assert "make price-history-proof-queue TOP_N=25" not in next_stage
    assert "make price-history-batch-closeout TOP_N=25" not in next_stage
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


def test_commercial_beta_continuation_prompt_is_persistent_but_evidence_bound():
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "Commercial Research Beta Continuation Contract" in roadmap
    assert "/goal" in prompt
    assert "codex/personal-research-mode-mvp" in prompt
    assert "pull/113" in prompt
    assert "commit `781ba2481` or a later verified descendant" in prompt
    assert "commit `54f3977d7` or a later verified descendant" in prompt
    assert "classify it once" in prompt
    assert "avoid identical retry loops" in prompt
    assert "Continue automatically while any safe, meaningful, in-scope local task remains" in prompt
    assert "Do not mark the objective complete" in prompt
    assert "Stage 1 — Answer-first workflow hardening" in prompt
    assert "Stage 6 — Operating maturity and product direction" in prompt
    assert "Never use `git add -A`" in prompt
    assert "Keep PR #113 draft" in prompt
    assert "Do not merge into main or deploy publicly without explicit approval" in prompt
    assert "Generated CSV, JSON" in prompt
    assert "Point-in-time consensus and rights: `permitted_point_in_time_consensus_and_rights_required`" in prompt
    assert "Hosted account and controls: `hosted_account_and_controls_required`" in prompt
    assert "Independent reviewers: `independent_reviewers_required`" in prompt
    assert "Trusted peer/source review: `trustworthy_peer_source_and_review_required`" in prompt
    assert "Calibration cohort: `calibration_cohort_required`" in prompt
    assert "Operated owner/incident/rollback capacity: `operated_owner_incident_rollback_capacity_required`" in prompt
    assert "Research-only; no investment advice" in prompt
    assert "Keep the goal active whenever any applicable gate remains incomplete or unproven" in prompt


def test_consensus_source_review_docs_keep_review_collection_and_activation_separate():
    roadmap = _read("ROADMAP.md")
    data_strategy = _read("docs/DATA_STRATEGY.md")
    pilot = _read("docs/EARNINGS_NOWCAST_PILOT.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, data_strategy, pilot, methodology, provenance, prompt):
        assert "earnings-consensus-source-review" in text
        assert "collection preview" in text.lower()
        assert "read-only" in text.lower()
    assert "explicit provider" in roadmap.lower()
    assert "original one-based" in provenance.lower()
    assert "auto_apply=false" in pilot
    assert "source-review-before-preview" in prompt.lower()


def test_consensus_source_review_docs_use_distinct_source_and_collection_inputs():
    data_strategy = _read("docs/DATA_STRATEGY.md")
    pilot = _read("docs/EARNINGS_NOWCAST_PILOT.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (data_strategy, pilot, prompt):
        assert "SOURCE_INPUT=<reviewed_source_export.csv>" in text
        assert "COLLECTION_INPUT=<prospective_consensus.csv>" in text
        assert "distinct input contracts" in text.lower()
        assert "earnings-consensus-source-review INPUT=<reviewed.csv>" not in text


def test_quarterly_cash_generation_docs_preserve_no_file_and_market_maturity_boundaries():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal_mode = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "cash from operations + reported capital expenditures" in methodology
    assert "explicit_filed_quarter" in provenance
    assert "no new data file, writer, template, or generated artifact" in provenance
    assert "reviewed quarterly source adapter" in personal_mode
    assert "methodology maturity" in roadmap
    assert "does not prove broad real-company coverage or market validation" in roadmap
    assert (
        "Quarterly cash-generation source adapter: `one_company_source_preview_accepted_for_review`"
        in prompt
    )
    assert "no supplemental data file" in prompt


def test_quarterly_adapter_acceptance_docs_keep_review_and_activation_separate():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal_mode = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "accepted_for_review is not production activation" in methodology
    assert "production_activation=false" in provenance
    assert "readiness_promotions=()" in provenance
    assert "no adapter file is loaded or written" in personal_mode
    assert "one-company adapter acceptance harness" in roadmap
    assert "bounded exact-source review" in roadmap
    assert "They do **not** prove production activation" in roadmap
    assert "Quarterly adapter acceptance" in prompt
    assert "accepted_for_review" in prompt


def test_mobile_research_first_action_docs_preserve_readiness_and_market_boundaries():
    personal_mode = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "mobile first-action density" in personal_mode.lower()
    assert "does not change readiness" in personal_mode.lower()
    assert "phone first-action" in roadmap.lower()
    assert "mobile first-action density" in prompt.lower()


def test_personal_research_evidence_detours_preserve_workspace_and_return_path():
    roadmap = _read("ROADMAP.md")
    personal_mode = _read("docs/PERSONAL_RESEARCH_MODE.md")
    dashboard_qa = _read("docs/DASHBOARD_QA.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, personal_mode, dashboard_qa, prompt):
        assert "Data Health and Proof History stay inside Personal Research mode" in text
        assert "Return to Company Workbench" in text
        assert "does not change readiness" in text


def test_pilot_freshness_docs_fail_closed_on_declared_source_dates():
    data_strategy = _read("docs/DATA_STRATEGY.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (data_strategy, roadmap, prompt):
        assert "declared source dates" in text.lower()
        assert "file mtimes" in text.lower()
        assert "make readiness-preview TOP_N=20" in text
        assert "does not make saved readiness current" in text.lower()
    assert "does not rebuild readiness" in data_strategy.lower()
    assert "make readiness" in prompt


def test_stale_readiness_continuation_gate_docs_keep_rankings_non_executable():
    roadmap = _read("ROADMAP.md")
    data_strategy = _read("docs/DATA_STRATEGY.md")
    dashboard_qa = _read("docs/DASHBOARD_QA.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, data_strategy, dashboard_qa, prompt):
        lowered = text.lower()
        assert "stale readiness continuation gate" in lowered
        assert "make readiness-preview TOP_N=20" in text
        assert "planning context only" in lowered
        assert "separate intentional reviewed write" in lowered
    assert "does not refresh data" in roadmap.lower()
    assert "does not prove market validation" in roadmap.lower()
    assert "auto-refresh status" in roadmap.lower()
    assert "session source preflight" in roadmap.lower()
    assert "commercial-beta release" in roadmap.lower()
    assert "auto-refresh status" in prompt.lower()
    assert "session source preflight" in prompt.lower()
    assert "advanced data health cards" in roadmap.lower()
    assert "advanced data health cards" in dashboard_qa.lower()
    assert "advanced data health cards" in prompt.lower()


def test_readiness_promotion_evidence_docs_keep_technical_and_rights_states_independent():
    roadmap = _read("ROADMAP.md")
    data_strategy = _read("docs/DATA_STRATEGY.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, data_strategy, methodology, provenance, prompt):
        lowered = text.lower()
        assert "technical" in lowered
        assert "commercial" in lowered
        assert "field" in lowered
        assert "make readiness" in text
    assert "composite or unregistered source values" in data_strategy.lower()
    assert "does not establish price-source provenance" in provenance
    assert "local_evidence_review_required" in prompt
    assert "not current readiness counts or rebuild approval" in roadmap


def test_readiness_change_cause_docs_explain_method_fit_without_company_judgment():
    roadmap = _read("ROADMAP.md")
    data_strategy = _read("docs/DATA_STRATEGY.md")
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, data_strategy, methodology, provenance, prompt):
        lowered = text.lower()
        assert "transition" in lowered
        assert "method" in lowered
        assert "current readiness totals" in lowered
    assert "acquisition/spac" in methodology.lower()
    assert "not a negative company signal" in roadmap.lower()
    assert "cannot alter scope" in prompt.lower()


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


def test_sec_cash_generation_pilot_docs_preserve_review_boundary():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    strategy = _read("docs/DATA_STRATEGY.md")
    personal = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "explicit_filed_table_outflow" in methodology
    assert "acceptanceDateTime" in provenance
    assert "sec_companyfacts" in strategy
    assert "accepted_for_review is not production activation" in personal
    assert "NVIDIA Q1 FY2027" in roadmap
    assert "does not activate Company Workbench" in roadmap
    assert "sec-quarterly-cash-preview" in prompt
    assert "do not repeat the NVIDIA pilot" in prompt


def test_company_workbench_cash_preview_docs_preserve_explicit_no_activation_boundary():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "cash_preview=1" in personal
    assert "Cash-generation review preview" in personal
    assert "not production evidence" in personal
    assert "production_activation=false" in provenance
    assert "readiness_promotions=()" in provenance
    assert "no canonical persistence" in provenance
    assert "complete withholding" in methodology
    assert "Advanced-only technical lineage" in methodology
    assert "one explicit user-flow composition" in roadmap
    assert "does not prove a second company" in roadmap
    assert "do not repeat the NVIDIA pilot" in prompt
    assert "bounded second-company proof" in prompt


def test_evidence_integrity_docs_preserve_fail_closed_valuation_and_cutoff_backtest_boundary():
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    safeguards = (
        "reject non-finite valuation inputs",
        "require a canonical real `YYYY-MM-DD` denominator period end",
        "reject blank, malformed, and non-calendar denominator period ends",
        "reject post-cutoff retrieval evidence",
        "canonicalize Revenue/EPS independently through explicit `supersedes_source_ref` lineage",
        "retain one event per ticker/period",
        "withhold ambiguous leaves per metric so one metric does not suppress the other",
        "use cutoff-bounded prior-year benchmarks so post-cutoff revisions cannot leak",
    )

    for text in (roadmap, methodology, prompt):
        for safeguard in safeguards:
            assert safeguard in text

    assert (
        "Evidence-integrity hardening anchor: commit `7d463bae7` or a later verified descendant"
        in prompt
    )


def test_prospective_field_proof_docs_preserve_stage_a_recording_boundary():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    operator = _read("docs/OPERATOR_GUIDE.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    commands = (
        "make prospective-field-proof-status",
        "make prospective-field-proof-preview",
        "make prospective-field-proof-record",
    )
    for text in (readme, roadmap, operator, prompt):
        for command in commands:
            assert command in text
        lowered = text.lower()
        assert "prospective-only" in lowered
        assert "legacy narrative proof is not upgraded" in lowered
        assert "absent ledger is a valid empty state" in lowered
        assert "technical_write_eligible" in text
        assert "commercial_evidence_eligible" in text
        assert "preview receipt" in lowered
        assert "ledger, input, cutoff, commercial mode, and source-rights registry" in lowered
        assert "does not activate readiness" in lowered

    assert "No sample field-proof rows are checked in" in readme
    assert "No sample field-proof rows are checked in" in roadmap
    assert (
        "The implemented structured per-ticker/per-field record is prospective-only"
        in prompt
    )
    assert "structured per-ticker/per-field proof record is prospective future work" not in prompt
    assert "No sample field-proof rows are checked in" in operator
    assert not Path("data/prospective_field_proofs.csv").exists()

    for text in (roadmap, operator, prompt):
        lowered = text.lower()
        assert "does not update canonical data" in lowered
        assert "does not update proof-readiness reconciliation" in lowered
        assert "does not activate company workbench" in lowered
        assert "separate design" in lowered

    assert "cooperative local locking" in operator.lower()
    assert "not crash-safe" in operator.lower()
    assert "not a database transaction" in operator.lower()
    assert "writers that do not cooperate" in operator.lower()


def test_release_docs_distinguish_tracked_and_excluded_readiness_snapshots():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")

    assert "For 10-20 external reviewer sessions" in readme
    assert "For 5-10 external reviewer sessions" not in readme
    assert "`make pilot-readiness-packet` writes `outputs/pilot_readiness_packet.md`" in readme
    assert "`make pilot-readiness-packet` is not read-only" in readme

    assert "tracked June 7 readiness snapshot" in roadmap
    assert "excluded July 21 local generated working-data snapshot" in roadmap
    assert "remains stale under this roadmap's declared-date policy" in roadmap
    assert "zero stable readiness changes" in roadmap
    assert "not committed PR evidence" in roadmap
    assert "does not authorize staging or a readiness rebuild" in roadmap
    for stale_count in (
        "current inspection finds 152",
        "146/146 promotions",
        "current-snapshot audit reports 3,506",
        "read-only current snapshot reports 21,246",
    ):
        assert stale_count not in roadmap
    volatile_observation = re.compile(
        r"\b(?:current|last observed|last verified|remains)[^.\n]*"
        r"(?:\d{1,3}(?:,\d{3})+|\d+/\d+|\d+\s+"
        r"(?:\w+\s+){0,2}(?:snapshots|rows|promotions|conflicts|outcomes|tickers))",
        re.IGNORECASE,
    )
    assert not volatile_observation.search(roadmap)


def test_public_mobile_handoff_docs_cover_direct_open_loading_and_remove_stale_measurement():
    roadmap = _read("ROADMAP.md")
    dashboard_qa = _read("docs/DASHBOARD_QA.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, dashboard_qa, prompt):
        normalized = " ".join(text.split())
        assert "direct-open loading state" in normalized
        assert "Selected ticker -> `Use now` -> `Still withheld` -> `Open Data Health`" in normalized
        assert "44px" in normalized
        assert "at least 50px" in normalized
        assert "no horizontal overflow" in normalized
        assert "no traceback" in normalized
        assert "four-column layout" in normalized
        assert "836.53125px" not in text
        assert "7.46875px" not in text

    normalized_roadmap = " ".join(roadmap.split())
    normalized_qa = " ".join(dashboard_qa.split())
    normalized_prompt = " ".join(prompt.split())
    assert "does not change readiness, source, research, or generated-artifact state" in normalized_roadmap
    assert "does not prove hosted behavior, accessibility conformance" in normalized_roadmap
    assert "does not change readiness, source, research, or generated-artifact state" in normalized_qa
    assert "Neither form of local presentation evidence proves data freshness, source rights, hosted behavior, accessibility compliance, external reviewer behavior, or predictive validity" in normalized_qa
    assert "not hosted, accessibility-conformance, external-reviewer, freshness, demand, or market evidence" in normalized_prompt
    assert "changes no readiness, source, research, or generated-artifact state" in normalized_prompt
    assert "fresh screenshots and audit notes remain" not in dashboard_qa
    assert "earlier screenshots predate this regression fix" in dashboard_qa
    assert "no new screenshot artifact was created" in dashboard_qa


def test_continuation_docs_keep_maturity_lanes_and_external_unblocks_truthful():
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, prompt):
        assert "Stage A-G labels are continuation maturity lanes only" in text
        assert "do not replace the numbered Stage 0-6 exit gates" in text
        assert "Stage B — local field-proof audit and operator hardening" in text
        assert "no readiness mapping" in text.lower()
        assert "separate design" in text.lower()

    assert (
        "The next executable maturity choice is a separately designed Company Workbench activation preview"
        not in roadmap
    )
    assert "is the second approved local priority after legacy surface quarantine" in roadmap
    assert "Activation remains non-active and separately designed" in roadmap

    classifications = (
        "permitted_point_in_time_consensus_and_rights_required",
        "hosted_account_and_controls_required",
        "independent_reviewers_required",
        "trustworthy_peer_source_and_review_required",
        "calibration_cohort_required",
        "operated_owner_incident_rollback_capacity_required",
        "point_in_time_benchmark_universe_and_rights_required",
        "accessibility_manual_review_environment_required",
        "paper_position_lab_design_approval_required",
    )
    for classification in classifications:
        assert prompt.count(classification) == 1

    assert "Subagent review is engineering review only; no GitHub human reviews exist." in prompt
    assert "10-20 independent task-based reviewers" in prompt
    assert "one bounded reviewed peer relationship" in prompt
    assert "at least 100 leakage-safe out-of-sample events" in prompt
    assert "a named owner and directly rehearsed incident and rollback capacity" in prompt


def test_approved_next_stage_program_is_ordered_non_blocking_and_evidence_bound():
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    ordered_priorities = (
        "Priority 1 — Legacy portfolio, ranking, and action-language quarantine",
        "Priority 2 — Stage B field-proof audit and operator hardening",
        "Priority 3 — In-app research-record authoring",
        "Priority 4 — Point-in-time benchmark and universe foundation",
        "Priority 5 — One permitted consensus source and one reviewed peer relationship",
        "Priority 6 — Controlled hosted operating boundary",
        "Priority 7 — Accessibility evidence beyond screenshots",
        "Priority 8 — Independent workflow validation",
        "Priority 9 — Out-of-sample calibration cohort",
        "Priority 10 — Separately approved hypothetical paper-position laboratory",
    )

    for text in (roadmap, prompt):
        assert "Approved Next-Stage Maturity Program" in text
        positions = [text.index(priority) for priority in ordered_priorities]
        assert positions == sorted(positions)
        assert all(text.count(priority) == 1 for priority in ordered_priorities)
        assert "A blocked priority does not become complete" in text
        assert "move to the next safe executable priority" in text
        assert "at least 100 valid leakage-safe out-of-sample events" in text
        assert "Live brokerage remains out of scope" in text
        assert "earnings-consensus-collection-record" in text
        assert "append-only evidence record" in text
        assert "does not activate readiness or numerical probability" in text

    assert "automated generation cannot become reviewer-authored evidence" in roadmap
    assert "corporate actions, delistings, survivorship, and leakage" in roadmap
    assert "10-20 independent workflow sessions" in roadmap
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in roadmap
    assert "governed by the Approved Next-Stage Maturity Program" in roadmap
    assert "after the single reviewed relationship in Priority 5" in roadmap
    assert "provider-neutral control contracts" in prompt
    assert "provider-specific implementation" in prompt.lower()
    assert "separate approved design" in prompt


def test_external_dependency_entries_own_distinct_conditions_and_last_observed_evidence():
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    labels = (
        "Point-in-time consensus and rights",
        "Hosted account and controls",
        "Independent reviewers",
        "Trusted peer/source review",
        "Calibration cohort",
        "Operated owner/incident/rollback capacity",
        "Point-in-time benchmark/universe data and rights",
        "Accessibility manual-review environment",
        "Paper-position laboratory design approval",
    )
    bullets = {
        label: next(
            line for line in prompt.splitlines() if line.startswith(f"- {label}:")
        )
        for label in labels
    }
    for bullet in bullets.values():
        assert "Last observed:" in bullet
        assert "Exact unblock condition:" in bullet
        observed = bullet.split("Last observed:", 1)[1].split(
            "Exact unblock condition:", 1
        )[0]
        assert not re.search(r"\d", observed)

    hosted = bullets["Hosted account and controls"].lower()
    for required in ("host account", "verified url", "access controls", "isolation"):
        assert required in hosted
    for operated_only in (
        "health",
        "incident",
        "rollback",
        "audit",
        "retention",
        "entitlements",
        "monitoring",
    ):
        assert operated_only not in hosted

    operated = bullets["Operated owner/incident/rollback capacity"].lower()
    for required in (
        "named owner",
        "rehearsed incident",
        "rollback",
        "audit",
        "retention",
        "entitlements",
        "monitoring",
        "health-check",
    ):
        assert required in operated
    for hosted_only in ("host account", "verified url", "access controls", "isolation"):
        assert hosted_only not in operated

    reviewers = bullets["Independent reviewers"]
    assert "independent human GitHub review of PR #113" in reviewers
    assert "when a human submits review evidence" not in reviewers
    assert "generic human review evidence" not in reviewers.lower()


def test_research_decision_lab_release_docs_bind_local_completion_to_current_evidence():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    decision_prompt = _read("docs/internal/RESEARCH_DECISION_LAB_CONTINUATION_GOAL_PROMPT.md")
    commercial_prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    design = _read("docs/superpowers/specs/2026-07-22-research-decision-lab-design.md")
    browser_contract = _read("src/browser_qa_evidence.py")
    readme = _read("README.md")

    assert "Research plan -> evidence -> invalidation -> scenario -> review trigger -> learning" in methodology
    for lane in ("Plan", "Evidence", "Invalidation", "Scenario", "Review trigger", "Learning"):
        assert f"`{lane}`" in methodology
    assert "Decision Lab lanes remain independent" in methodology

    assert "Research Decision Lab Contract" in provenance
    assert "writes no journal, outcome, source, readiness, proof, report, screenshot, or timing artifact" in provenance
    assert "A valid lane cannot promote, repair, or clear another lane" in provenance

    assert "What Changed -> Research Decision Lab -> Business Trend" in personal
    assert "Weekly Research Summary -> Research Discipline Review -> Research change monitor" in personal
    assert "No process item is currently due from saved reviewer-authored evidence" in personal

    assert "Implemented locally — Research Decision Lab" in roadmap
    assert "Stage 4 — Documentation and release evidence: completed locally" in roadmap
    assert "Local Decision Lab implementation is complete" in decision_prompt
    assert "Local Decision Lab implementation is complete" in commercial_prompt
    assert "Status:** Implemented locally; external maturity gates remain separate" in design

    assert '"Research Decision Lab"' in browser_contract
    assert '"Research Discipline Review"' in browser_contract
    assert "Research Decision Lab" in readme
    assert "Research Discipline Review" in readme

    external_boundary = (
        "does not prove source coverage, predictive accuracy, investment performance, independent adoption, "
        "hosted reliability, commercial demand, competitive superiority, or product-market fit"
    )
    for text in (roadmap, decision_prompt, commercial_prompt):
        assert external_boundary in text


def test_legacy_research_utility_quarantine_is_consistent_across_product_docs():
    readme = _read("README.md")
    product_spec = _read("PRODUCT_SPEC.md")
    readiness = _read("READINESS_MODEL.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    design = _read("docs/superpowers/specs/2026-07-22-legacy-research-utility-quarantine-design.md")

    boundary = "Legacy research utility — not part of Personal Research Mode"
    for text in (readme, product_spec, readiness, roadmap, prompt, design):
        assert boundary in text

    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in readme
    assert "Operator-only legacy compatibility utilities" in product_spec
    assert "compatibility-only readiness rows" in readiness
    assert "Priority 1 — completed locally" in roadmap
    assert "Priority 2 — Stage B field-proof audit and operator hardening" in roadmap
    assert "Priority 1 is complete locally" in prompt
    assert "Priority 2 is complete locally" in prompt

    for text in (readme, product_spec, readiness):
        lowered = text.lower()
        assert "cannot feed research decision lab" in lowered
        assert "cannot change readiness" in lowered
        assert "cannot produce recommendations, sizing, or transaction behavior" in lowered


def test_stage_b_field_proof_audit_is_documented_as_read_only_and_no_mapping():
    readme = _read("README.md")
    operator = _read("docs/OPERATOR_GUIDE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    design = _read("docs/superpowers/specs/2026-07-22-field-proof-stage-b-audit-design.md")

    for text in (readme, operator, roadmap, prompt, design):
        assert "make prospective-field-proof-audit" in text
        assert "preview_receipt_persisted=false" in text
        assert "receipt_revalidation_required=true" in text

    assert "Stage B — completed locally" in roadmap
    assert "Priority 3 — In-app research-record authoring" in roadmap
    assert "Priority 2 is complete locally" in prompt
    assert "Priority 3 — completed locally after direct desktop/phone runtime review" in prompt

    for text in (operator, roadmap, prompt):
        lowered = text.lower()
        assert "does not activate readiness" in lowered
        assert "does not update canonical data" in lowered
        assert "does not activate company workbench" in lowered


def test_priority_three_authoring_release_docs_require_current_runtime_evidence_before_local_completion():
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    design = _read("docs/superpowers/specs/2026-07-22-in-app-research-record-authoring-design.md")
    plan = _read("docs/superpowers/plans/2026-07-22-in-app-research-record-authoring.md")
    readme = _read("README.md")
    product_spec = _read("PRODUCT_SPEC.md")

    assert "# In-App Research-Record Authoring Implementation Plan" in plan
    assert "REQUIRED SUB-SKILL" in plan
    assert "Validate -> Preview -> Confirm and save" in plan

    release_contract = (
        "Thesis, evidence, catalyst, and outcome records are all available in the collapsed Company Workbench composer.",
        "A valid record requires an exact preview and explicit confirmation before save.",
        "Drafts are untrusted and preview receipts are session-only.",
        "Production tests never append repository ledgers; persistence tests use temporary ledgers.",
        "A saved record cannot change readiness, forecasts, probabilities, recommendations, or any other ledger.",
    )
    historical_priority_contract = (
        "Priority 3 is complete locally only after all automated acceptance tests and direct desktop/phone review pass; Priority 4 is next and incomplete.",
        "Priority 4 exit requires one bounded permitted point-in-time dataset with rights, identity, corporate-action, delisting, survivorship, cutoff, reproduction, and leakage gates all passing.",
    )

    for text in (readme, product_spec, roadmap, prompt, design):
        for statement in release_contract:
            assert statement in text

    for statement in historical_priority_contract:
        assert statement in design

    current_priority_contract = (
        "Priority 4's local validator is frozen; its permitted real-data exit gate remains externally incomplete.",
        "Priority 6's provider-neutral authorization contract is complete locally; hosted implementation remains environment-dependent.",
        "Priority 7 accessibility remediation is the next safe executable local lane.",
    )
    for text in (readme, product_spec, roadmap, prompt):
        for statement in current_priority_contract:
            assert statement in text
        assert historical_priority_contract[0] not in text

    assert "selected `profile_key` and normalized ticker" in design
    assert "current ledger fingerprint" in plan.lower()


def test_active_product_docs_use_evidence_first_positioning_and_current_stage_truth():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "Evidence-First Research Workbench" in readme
    assert "serious individual equity researchers and small research teams" in readme
    assert (
        "Priority 7 accessibility remediation is the next safe executable local lane."
        in " ".join(methodology.split())
    )
    assert (
        "Last verified incoming synchronization anchor: "
        "`dcad75b9e4e3cdba24e5add58271a3f038e5ccc4`"
        in prompt
    )
    assert "incoming exact-head GitHub Actions run `30339299654` passed" in prompt
    assert "incoming local full-suite baseline reported 4,306 passing tests" in prompt

    for text in (readme, roadmap, methodology, prompt):
        assert "Priority 4 is next and incomplete" not in text
        assert "next executable local methodology lane is the\nprovider-neutral hosted-control contract in Priority 6" not in text


def test_current_roadmap_consensus_commands_match_makefile_required_inputs():
    roadmap = _read("ROADMAP.md")
    makefile = _read("Makefile")
    priority_five = roadmap.split(
        "### Priority 5 — One permitted consensus source and one reviewed peer relationship",
        maxsplit=1,
    )[1].split("### Priority 6", maxsplit=1)[0]
    source_target = makefile.split(
        "earnings-consensus-source-review:",
        maxsplit=1,
    )[1].split("earnings-consensus-collection-plan:", maxsplit=1)[0]
    record_target = makefile.split(
        "earnings-consensus-collection-record:",
        maxsplit=1,
    )[1].split("prospective-field-proof-status:", maxsplit=1)[0]

    assert '$(INPUT)' in source_target
    assert '$(PROVIDER)' in source_target
    assert '$(AS_OF)' in source_target
    assert (
        "make earnings-consensus-source-review "
        "INPUT=$SOURCE_INPUT PROVIDER=<source_id> AS_OF=<timestamp>"
        in priority_five
    )
    assert '$(INPUT)' in record_target
    assert (
        "make earnings-consensus-collection-record "
        "INPUT=$COLLECTION_INPUT AS_OF=<same-timestamp>"
        in priority_five
    )


def test_completed_priorities_are_not_reissued_as_implementation_work():
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    completed_section = prompt.split(
        "Priority 1 — Legacy portfolio, ranking, and action-language quarantine",
        maxsplit=1,
    )[1].split("Priority 4 — Point-in-time benchmark", maxsplit=1)[0]

    for stale_instruction in (
        "Inventory every Personal Research",
        "Remove those concepts from supported primary flows",
        "Complete the approved read-only audit",
        "Design and implement simple validate -> preview -> confirm authoring",
        "begin with Priority 1, then Priority 2",
    ):
        assert stale_instruction not in completed_section
        assert stale_instruction not in prompt

    assert (
        "Do not re-run Priorities 1-3 unless a current regression is directly reproduced."
        in prompt
    )


def test_current_handoff_routes_to_local_reliability_work_not_exhausted_price_queues():
    roadmap = _read("ROADMAP.md")
    next_stage = _read("docs/NEXT_STAGE_ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, next_stage, prompt):
        assert "Documentation and routing reconciliation is complete locally" in text
        assert "observation-recency UX repair" in text
        assert "framework reliability" in text

    assert "Finish this documentation/routing reconciliation once" not in prompt
    assert "Complete the documentation/routing reconciliation once" not in next_stage
    assert "make price-history-proof-queue" not in next_stage
    assert "make price-history-batch-closeout" not in next_stage
    assert (
        "Priority 7 accessibility remains the next numbered maturity priority"
        in roadmap
    )
    assert (
        "provider-neutral retention/deletion or audit-event work is not the active next lane"
        in prompt
    )


def test_completed_index_labels_local_prerequisites_without_claiming_external_exit():
    roadmap = _read("ROADMAP.md")

    assert "### P1 local prerequisite: Hosted operating contracts" in roadmap
    assert "### P1 local prerequisite: Independent beta protocol" in roadmap
    assert "### P1: Controlled Hosted Preview Verification" not in roadmap
    assert "### P1: Controlled Pilot Review" not in roadmap


def test_capability_audit_records_recency_as_implemented_and_keeps_quant_gate_open():
    audit = _read("docs/analysis_capability_audit.md")

    assert "observation-recency separation is implemented" in audit
    assert "shared provenance and recency eligibility" in audit
    assert "separate calculation readiness from observation recency" not in audit


def test_accessibility_evidence_records_same_page_skip_fix_without_overclaim():
    roadmap = _read("ROADMAP.md")
    evidence = _read("docs/ACCESSIBILITY_EVIDENCE.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (roadmap, evidence, prompt):
        assert 'target="_blank"' in text
        assert 'target="_self"' in text
        assert "#public-page-answer" in text
        assert "blocked_environment" in text

    assert "K01 and K02 therefore remain `blocked_environment`" in evidence
    assert "no complete keyboard-only traversal is claimed" in evidence
    assert "framework-control target-size audit" in evidence
    assert "exactly `24x24`" in evidence
    assert "enlarged the tooltip wrapper, not its nested" in evidence
    assert "`Open Data Health` at `102x24`" in evidence
    assert "does not prove pointer-spacing exceptions" in evidence
    assert "Priority 7 remains incomplete" in evidence


def test_priority_three_release_docs_record_controller_runtime_evidence_without_claiming_production_persistence():
    readme = _read("README.md")
    product_spec = _read("PRODUCT_SPEC.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")
    design = _read("docs/superpowers/specs/2026-07-22-in-app-research-record-authoring-design.md")

    completion = "Priority 3 — completed locally after direct desktop/phone runtime review and the required automated acceptance matrix."
    assert completion in roadmap
    assert completion in prompt
    assert completion in design

    assert "Desktop `1280x720`: `clientWidth=scrollWidth=1280`." in design
    assert "Phone `390x844`: `clientWidth=scrollWidth=390`." in design
    assert "No successful production save was attempted; persistence evidence remains temporary-ledger AppTest and direct persistence tests only." in design
    assert "`6b7cdbd3b`, `996d86610`, `10c2c155c`, and `e67b16d04`" in design
    assert "Commit identifier will be added only after the corresponding commit exists." not in design

    hardening = (
        "Hardening commit `07758114c` closes the confirmation race: all three append engines "
        "share one resolved-ledger cooperative lock, receipts bind resolved ledger identity, "
        "every new preview resets confirmation, and uncertain post-append teardown requires "
        "one-shot read-side reload before success."
    )
    for text in (roadmap, prompt, design):
        assert hardening in text

    integrity = (
        "Final integrity commit `e3a090dba` ensures confirmation appends only the "
        "receipt-matched recomputed record and enforces one readable active thesis lineage: "
        "revisions must supersede the exact active entry and preserve its thesis ID. The Company "
        "Workbench locks and explains that relationship, with temporary-ledger create -> revise "
        "-> reload coverage."
    )
    for text in (readme, product_spec, roadmap, prompt, design):
        assert integrity in text

    confirmation_integrity = (
        "Confirmation-integrity commit `5a6c55921` binds every displayed preview field, "
        "preview time, and destination label to the exact receipt. If an append raises after "
        "it may have written, confirmation returns one-shot `save_pending_reload` with the exact "
        "record ID unless the locked ledger is provably unchanged; it never invites a blind "
        "duplicate retry."
    )
    for text in (readme, product_spec, roadmap, prompt, design):
        assert confirmation_integrity in text


def test_accessibility_task_protocol_is_reproducible_and_cannot_claim_conformance_from_incomplete_runs():
    protocol = _read("docs/ACCESSIBILITY_TASK_PROTOCOL.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    required_protocol = (
        "commit SHA",
        "Research Desk -> Discover -> Company Workbench -> Monitor",
        "keyboard_only",
        "zoom_200",
        "zoom_400",
        "forced_colors",
        "reduced_motion",
        "screen_reader",
        "passed_direct",
        "blocked_environment",
        "No result may be inferred from a screenshot",
        "Do not save a research record",
        "No WCAG conformance claim",
    )
    for phrase in required_protocol:
        assert phrase in protocol

    for text in (roadmap, prompt):
        assert "docs/ACCESSIBILITY_TASK_PROTOCOL.md" in text
        assert "the protocol is not completion evidence" in text


def test_priority_four_approved_design_preserves_point_in_time_and_no_write_boundaries():
    design_path = (
        "docs/superpowers/specs/"
        "2026-07-23-point-in-time-universe-foundation-design.md"
    )
    design = _read(design_path)
    roadmap = _read("ROADMAP.md")
    prompt = _read(
        "docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md"
    )
    normalized_design = " ".join(design.split())

    required_design = (
        "Stable security identifier; never derived from ticker",
        "`complete_snapshot` or `event_history`",
        "`raw`, `normalized`, `excluded`, and `analysis_eligible`",
        "`source_rights_eligibility`",
        "`reproduction_ready`",
        "`leakage_safe`",
        "membership_count_and_sha256_at_cutoff_v1",
        "create no directory or artifact",
        "Synthetic fixtures prove software behavior only",
        "does not satisfy that exit gate by itself",
    )
    for phrase in required_design:
        assert phrase in normalized_design

    for text in (roadmap, prompt):
        assert design_path in text
        assert "current ticker-centric universe" in text
        assert "Synthetic fixtures remain test-only" in text


def test_priority_four_local_validator_is_documented_without_claiming_real_data_completion():
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    prompt = _read(
        "docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md"
    )
    implementation = (
        "Implemented locally: read-only immutable-package status/preview with ten "
        "independent states: manifest, technical, temporal, identity, membership, "
        "corporate action, delisting, source rights, reproduction, and leakage."
    )
    synthetic_boundary = (
        "Synthetic fixtures remain test-only and local software evidence cannot "
        "complete Priority 4."
    )
    real_data_exit = (
        "Priority 4 remains open until one bounded permitted real dataset is "
        "independently reviewed, reproduces the expected membership count and digest, "
        "and passes rights, identity, corporate-action, delisting, survivorship, "
        "cutoff, partition, reproduction, and leakage gates."
    )
    independent_readiness = (
        "This local evidence does not change independent readiness for actuals, "
        "consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, or "
        "calibration."
    )
    research_boundaries = (
        "It does not provide investment advice; numerical probability remains "
        "unavailable without calibration; Q4 evidence and EPS split-basis "
        "compatibility remain explicit; synthetic evidence stays test-only; candidate "
        "peer evidence remains candidate-context-only."
    )
    commands = {
        "make point-in-time-universe-status MANIFEST=<path>",
        "make point-in-time-universe-preview MANIFEST=<path> TOP_N=20",
    }

    for text in (roadmap, methodology, prompt):
        assert implementation in text
        assert "membership_count_and_sha256_at_cutoff_v1" in text
        assert synthetic_boundary in text
        assert text.count(real_data_exit) == 1
        assert independent_readiness in text
        assert research_boundaries in text
        assert set(
            re.findall(r"`(make point-in-time-universe-[^`]+)`", text)
        ) == commands

    assert "Priority 4 is complete" not in roadmap
    assert "Priority 4 is complete" not in methodology
    assert "Priority 4 is complete" not in prompt
    assert "Priority 4 — completed" not in roadmap
    assert "Priority 4 — completed" not in prompt

    assert "Start from current repository truth, not chat memory." in prompt
    assert (
        "Verify authoritative remote commit "
        "`69c49968e77bfd55fa259695089e1f34ac2fddfb` or a later descendant "
        "before relying on this implementation evidence."
    ) in prompt
    assert "exact-head GitHub Actions run `30185232040` passed" in prompt
    assert (
        "compare the actual product tree and remote PR head instead of recommitting "
        "an already synchronized package"
    ) in prompt
    assert (
        "Point-in-time universe production-validator lineage anchor: commit "
        "`1361472bce6d23cc537ef222c3735bb640c9838a`"
    ) in prompt
    assert (
        "When external evidence is unavailable, record its exact unblock condition "
        "once and continue to the next safe executable lane."
    ) in prompt
    assert (
        "Never claim overall completion without direct current evidence for every "
        "applicable exit gate."
    ) in prompt
    assert (
        "Do not run readiness rebuilds or generated-artifact commands without "
        "explicit approval."
    ) in prompt


def test_priority_four_resource_budgets_and_review_state_are_documented_truthfully():
    roadmap = _read("ROADMAP.md")
    methodology = _read("docs/METHODOLOGY.md")
    prompt = _read(
        "docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md"
    )
    history = _read("docs/internal/POINT_IN_TIME_UNIVERSE_REVIEW_HISTORY.md")
    prior_review_closures = (
        "The second through fourth fresh whole-branch reviews drove the raw-row "
        "rights, cutoff-relative history, publication chronology, immutable "
        "bounded-read, aggregate-budget, and structured-input parser closures."
    )
    budgets = (
        "Local resource budgets for one supplied package: preview sample 100 rows; "
        "manifest 1 MiB; each contract CSV 32 MiB; four contract snapshots combined "
        "64 MiB; source-rights registry 4 MiB; declared rows 250,000 per contract; "
        "package traversal 32 entries."
    )
    scope_boundary = (
        "These local bounds do not prove scale, hosted reliability, or market "
        "readiness."
    )
    external_gate = (
        "No permitted independently reviewed real dataset, accepted expected "
        "count/digest, or source-rights proof is on record."
    )
    v5_findings = (
        "The fifth fresh whole-branch review confirmed those closures and found "
        "three Important trust-boundary defects: C0/C1 characters in structural "
        "identifiers could render the newline-delimited membership digest ambiguous "
        "and forge public status lines, while manifest creation could predate its "
        "cutoff or bound evidence."
    )
    v5_remediation = (
        "Commits `b2bbd9961` and `c643d066b` remediate those V5 findings locally "
        "with one shared C0/C1 plus Unicode line/paragraph-separator boundary, "
        "safe structural-token rendering, an explicit "
        "creation-at-or-after-cutoff manifest gate, and exact-row chronology "
        "against every contract timestamp."
    )
    first_review_follow_up = (
        "The first independent R7 review found the Unicode separator and "
        "`listing_state_after` bypass gaps; `c643d066b` closes them locally."
    )
    v6_finding = (
        "The sixth fresh whole-branch review confirmed those closures and found "
        "one remaining Important non-scalar input defect: lone Unicode surrogate "
        "code points could reach public output."
    )
    v6_remediation = (
        "Commit `f143d48ed` rejects Unicode category `Cs` through the shared "
        "boundary and defensively ASCII-escapes it while valid "
        "supplementary-plane scalars remain deterministic."
    )
    v7_findings = (
        "The seventh fresh whole-branch review confirmed the V6 correction and "
        "found four further trust-boundary defects (two Critical, one Important, "
        "and one Minor): duplicate JSON/YAML mapping keys could silently change "
        "manifest and rights meaning; invalid or unresolved successor and "
        "listing-state evidence could authorize stale original-member digests; "
        "malformed CSV headers could discard contract bodies and continue; and "
        "non-RFC3339 manifest or policy timestamps were accepted."
    )
    v7_remediation = (
        "The local seventh-review remediation rejects duplicate keys at every "
        "mapping depth, requires strict RFC3339 UTC manifest and policy "
        "timestamps with at most six fractional-second digits, stops malformed "
        "headers as package-level input-identity failures, and enforces explicit "
        "policy/event/listing-state, successor-identity, and "
        "membership-consistency gates without inferring or repairing a successor "
        "or membership."
    )
    scoped_review_state = (
        "An independent scoped re-review then confirmed the four original findings "
        "and the two compatibility regressions were addressed."
    )
    eighth_review_state = (
        "The eighth fresh whole-branch review then found three Critical, nine "
        "Important, and two Minor defects across sub-microsecond ordering, event-time "
        "identity, listing chronology and rights, walk-forward bootstrap aggregation, "
        "identity/action reconciliation, eligible provenance, package-contained "
        "bounded reads, manifest type handling, standalone rights loading, and "
        "literal-safe Make arguments."
    )
    eighth_remediation_state = (
        "Remediation 9A through 9G closed every finding test-first. Independent scoped "
        "re-reviews confirmed no remaining Critical or Important finding in each "
        "corrected scope; the two Minor contracts now reject identical issuer/security "
        "IDs and recursively freeze manifest semantics."
    )
    freeze_reconciliation = (
        "Freeze reconciliation consolidated 21 overlapping remediation test files "
        "into six domain suites and one shared fixture module, removed one exact "
        "duplicate plus cross-remediation private imports, and closed five additional "
        "local correctness gaps: ambiguous parents cannot authorize forks; pre-action "
        "cutoffs do not poison later required coverage; decision-consumed "
        "listing-state evidence is retained in eligible provenance; manifest nesting "
        "is explicitly bounded; and structural source IDs cannot forge status output."
    )
    local_verification = (
        "Full branch verification at freeze reconciliation is 4,084 passing tests, "
        "one environment-limited socket test skipped, and one existing dependency "
        "deprecation warning."
    )
    remaining_boundary = (
        "The final fresh whole-slice review found one Important cutoff-relative "
        "event regression; it was reproduced, fixed, and confirmed closed with no "
        "remaining Critical or Important issue. The consolidated package was "
        "synchronized at `69c49968e77bfd55fa259695089e1f34ac2fddfb`, and exact-head "
        "GitHub Actions run `30185232040` passed"
    )
    remaining_external_boundary = (
        "Real-data evidence remains pending; Priority 4 remains externally incomplete."
    )
    controlled_failures = (
        "Duplicate JSON/YAML mapping keys and malformed contract headers also "
        "fail nonzero, traceback-free, and write-free through the direct "
        "validator and CLI/Make boundaries."
    )

    normalized_history = " ".join(history.split())
    for statement in (
        prior_review_closures,
        v5_findings,
        v5_remediation,
        first_review_follow_up,
        v6_finding,
        v6_remediation,
        v7_findings,
        v7_remediation,
        scoped_review_state,
        eighth_review_state,
        eighth_remediation_state,
        freeze_reconciliation,
        local_verification,
        remaining_boundary,
        remaining_external_boundary,
        controlled_failures,
        budgets,
        scope_boundary,
        external_gate,
    ):
        assert statement in normalized_history

    history_link = "docs/internal/POINT_IN_TIME_UNIVERSE_REVIEW_HISTORY.md"
    for text in (roadmap, methodology, prompt):
        normalized = " ".join(text.split())
        assert history_link in text
        assert "Priority 4 remains externally incomplete" in normalized
        assert budgets in normalized
        assert scope_boundary in normalized
        assert external_gate in normalized
        assert prior_review_closures not in normalized
        assert v5_findings not in normalized
        assert eighth_review_state not in normalized
        assert freeze_reconciliation not in normalized

    assert prior_review_closures in normalized_history
    assert v5_findings in normalized_history
    assert v5_remediation in normalized_history
    assert first_review_follow_up in normalized_history
    assert v6_finding in normalized_history
    assert v6_remediation in normalized_history
    assert v7_findings in normalized_history
    assert v7_remediation in normalized_history
    assert scoped_review_state in normalized_history
    assert eighth_review_state in normalized_history
    assert eighth_remediation_state in normalized_history
    assert freeze_reconciliation in normalized_history
    assert local_verification in normalized_history
    assert remaining_boundary in normalized_history
    assert remaining_external_boundary in normalized_history
    assert controlled_failures in normalized_history
    assert budgets in normalized_history
    assert scope_boundary in normalized_history
    assert external_gate in normalized_history
