from pathlib import Path


BANNED_EXECUTION_TOKENS = (
    "def place_order(",
    "def submit_order(",
    "def execute_trade(",
    "def route_order(",
    "alpaca",
    "interactivebrokers",
    "ibkr",
)

BANNED_RECOMMENDATION_PHRASES = (
    "buy now",
    "sell now",
    "strong buy",
    "guaranteed return",
    "buy recommendation",
    "sell recommendation",
    "hold recommendation",
)


def test_no_trade_execution_module_or_order_placement_was_introduced():
    root = Path("src")
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    lowered = source_text.lower()
    for token in BANNED_EXECUTION_TOKENS:
        assert token not in lowered


def test_stock_report_workflow_does_not_introduce_direct_recommendation_language():
    guarded_paths = (
        Path("src/stock_report.py"),
        Path("src/valuation.py"),
        Path("src/dashboard.py"),
        Path("src/monthly_picks.py"),
        Path("src/track_record.py"),
        Path("src/providers/market_data.py"),
        Path("src/providers/local_market_data.py"),
        Path("src/providers/sec_companyfacts.py"),
    )
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in guarded_paths)
    lowered = source_text.lower()
    for phrase in BANNED_RECOMMENDATION_PHRASES:
        assert phrase not in lowered


def test_gitignore_covers_local_runtime_artifacts():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    expected_entries = (
        "data/cache/",
        "data/backups/",
        "data/imports/*.csv",
        "!data/imports/.gitkeep",
        "outputs/*stock_report.json",
        "outputs/project_status.json",
        "outputs/project_status_summary.csv",
        "outputs/project_status_top_actions.csv",
        "outputs/project_status_next_steps.csv",
        "local_artifacts_backup/",
        "AGENTS.md",
        ".agents/",
        "docs/CODEX_SKILLS_OVERVIEW.md",
    )
    for entry in expected_entries:
        assert entry in gitignore


def test_internal_agent_reference_files_are_not_public_release_artifacts():
    internal_paths = (
        Path("AGENTS.md"),
        Path(".agents"),
        Path("docs/CODEX_SKILLS_OVERVIEW.md"),
    )
    tracked_or_present = [path for path in internal_paths if path.exists()]
    assert tracked_or_present == []


def test_public_readme_contains_research_only_guardrails():
    readme_text = Path("README.md").read_text(encoding="utf-8").lower()
    expected_phrases = (
        "research-only guardrails",
        "not a trading system",
        "connect to brokers",
        "recommend option trades",
        "provide direct buy/sell instructions",
        "fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations",
    )
    for phrase in expected_phrases:
        assert phrase in readme_text
