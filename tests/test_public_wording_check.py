from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_public_wording_module():
    module_path = Path("scripts/public_wording_check.py")
    spec = importlib.util.spec_from_file_location("public_wording_check", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_wording_allows_research_only_guardrails():
    module = load_public_wording_module()
    text = "\n".join(
        [
            "This is investment research software, not investment advice and not a trading system.",
            "It does not place orders, connect to brokers, route trades, or auto-trade.",
            "Research-only: no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions.",
            "No options recommendations.",
        ]
    )

    assert module.find_forbidden_matches(text, path="README.md") == []


def test_public_wording_flags_direct_advice_and_execution_claims():
    module = load_public_wording_module()
    text = "\n".join(
        [
            "We recommend buy this stock.",
            "Buy now after the dashboard loads.",
            "The app can place orders.",
            "Auto-trading system enabled.",
            "It connects to a broker.",
            "Suggest options trade setup.",
        ]
    )

    matches = module.find_forbidden_matches(text, path="README.md")
    rules = {match.rule for match in matches}

    assert {
        "direct_recommendation",
        "direct_buy_call",
        "order_execution",
        "auto_trading_enabled",
        "broker_connection_enabled",
        "options_advice",
    } <= rules


def test_public_wording_flags_internal_tooling_and_stale_repo_references():
    module = load_public_wording_module()
    text = "\n".join(
        [
            "Old repo: https://github.com/davidjiang8888/Stock-Analysis",
            "Codex internal thread notes should not appear here.",
            "Assistant skills can help development review.",
            "Public Equity Investing and Investment Banking plugins were installed.",
            "Draft PR #1: https://github.com/YuzeJ21/Stock-Analysis/pull/1",
            "Public repo: https://github.com/YuzeJ21/Stock-Analysis",
        ]
    )

    matches = module.find_forbidden_matches(text, path="README.md")
    rules = {match.rule for match in matches}

    assert {
        "old_github_owner",
        "codex_internal",
        "assistant_skill_leak",
        "internal_pr_note",
    } <= rules
    assert not any(match.text == "Public repo: https://github.com/YuzeJ21/Stock-Analysis" for match in matches)


def test_public_wording_scan_scope_is_public_but_not_tests_or_generated_csvs():
    module = load_public_wording_module()
    paths = {path.as_posix() for path in module.public_paths(Path("."))}

    assert "README.md" in paths
    assert "docs/assets/dashboard-preview.svg" in paths
    assert "src/dashboard.py" in paths
    assert "src/stock_report.py" in paths
    assert "outputs/stock_reports/nvda.md" in paths
    assert "tests/test_launchers.py" not in paths
    assert "outputs/research_decisions.csv" not in paths
    assert "data/reports/ticker_readiness_report.csv" not in paths


def test_dashboard_preview_asset_uses_three_public_paths_in_order():
    svg = Path("docs/assets/dashboard-preview.svg").read_text(encoding="utf-8")

    review_index = svg.index("Review one stock: make stock-report-md TICKER=NVDA")
    improve_index = svg.index("Improve data coverage: trusted-data candidate list")
    explore_index = svg.index("Explore ready names: Monthly Picks and sample reports")

    assert review_index < improve_index < explore_index
    assert "Stock Research Command Center dashboard preview" in svg
    assert "research-only" in svg


def test_public_wording_report_is_read_only_and_concise():
    module = load_public_wording_module()
    clean_report = module.build_report(3, [])

    assert "Public Wording Check" in clean_report
    assert "Read-only" in clean_report
    assert "internal development-tool" in clean_report
    assert "Public wording check passed." in clean_report
    assert "Scanned public files: 3" in clean_report
    assert "no broker integration" in clean_report

    failed_report = module.build_report(
        1,
        [module.WordingMatch(path="README.md", line_number=12, rule="direct_buy_call", text="Buy now.")],
    )

    assert "Public wording check failed." in failed_report
    assert "README.md:12 [direct_buy_call] Buy now." in failed_report
