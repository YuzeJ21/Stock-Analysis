import json
import sys
from pathlib import Path
from urllib.error import URLError

import pandas as pd

from src.session_source_preflight import (
    build_session_source_preflight,
    load_session_source_preflight,
    main,
    probe_fmp_key,
    probe_finnhub_key,
    render_session_source_preflight,
    session_source_preflight_output_path,
)


def _write_fundamentals(root: Path, rows: list[dict[str, object]]) -> None:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(data_dir / "fundamentals.csv", index=False)


def test_session_source_preflight_prefers_sec_lane_when_sec_is_available(tmp_path: Path):
    def sec_probe(_user_agent: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason_code": "ok",
            "detail": "HTTP 200",
            "next_action": "",
        }

    def yfinance_import_probe() -> dict[str, object]:
        return {
            "status": "available",
            "reason_code": "installed",
            "detail": "yfinance 0.2.99",
            "next_action": "",
        }

    def yfinance_stage_probe() -> dict[str, object]:
        return {
            "status": "available",
            "reason_code": "probe_succeeded",
            "detail": "Resolved MSFT.",
            "next_action": "",
        }

    preflight = build_session_source_preflight(
        tmp_path,
        sec_user_agent="Research Tester test@example.com",
        sec_probe=sec_probe,
        yfinance_import_probe=yfinance_import_probe,
        yfinance_stage_probe=yfinance_stage_probe,
    )

    assert preflight["session_flags"] == []
    assert preflight["preferred_lane_order"][0] == "sec_fundamentals_share_count"
    assert "peer_mapping_proof" in preflight["available_lanes"]
    assert preflight["sources"]["sec"]["status"] == "available"


def test_session_source_preflight_prefers_local_fundamentals_when_sec_is_unavailable(tmp_path: Path):
    _write_fundamentals(
        tmp_path,
        [
            {"ticker": "ALOY", "source": "reviewed_manual", "revenue": 123.0, "shares_outstanding": 1000.0},
            {"ticker": "CRDO", "source": "sec_companyfacts", "revenue": 456.0, "shares_outstanding": 2000.0},
        ],
    )
    (tmp_path / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "reports" / "ticker_readiness_report.csv").write_text(
        "\n".join(
            [
                "ticker,missing_data",
                "ALOY,dcf: shares_outstanding",
                "CRDO,dcf: revenue",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def sec_probe(_user_agent: str) -> dict[str, object]:
        return {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": str(URLError("dns failed")),
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        }

    def yfinance_import_probe() -> dict[str, object]:
        return {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        }

    preflight = build_session_source_preflight(
        tmp_path,
        sec_user_agent="Research Tester test@example.com",
        sec_probe=sec_probe,
        yfinance_import_probe=yfinance_import_probe,
    )

    assert set(preflight["session_flags"]) == {"session_sec_unavailable", "session_yfinance_unavailable"}
    assert preflight["preferred_lane_order"][0] == "local_reviewed_fundamentals_share_count"
    assert preflight["sources"]["local_fundamentals"]["row_count"] == 2
    assert preflight["sources"]["local_fundamentals"]["share_count_fixable_ticker_count"] == 1
    assert preflight["sources"]["local_fundamentals"]["fundamentals_fixable_ticker_count"] == 1
    assert set(preflight["do_not_retry_paths"]) == {"sec", "yfinance_fundamentals"}


def test_session_source_preflight_reports_fixable_counts_for_local_rows(tmp_path: Path):
    _write_fundamentals(
        tmp_path,
        [
            {"ticker": "ABLV", "source": "reviewed_manual", "revenue": 111.0, "free_cash_flow": 22.0},
            {"ticker": "ABOS", "source": "reviewed_manual", "shares_outstanding": 222.0},
        ],
    )
    (tmp_path / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "reports" / "ticker_readiness_report.csv").write_text(
        "\n".join(
            [
                "ticker,missing_data",
                "ABLV,dcf: revenue; free cash flow",
                "ABOS,dcf: shares_outstanding",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    preflight = build_session_source_preflight(
        tmp_path,
        sec_probe=lambda _user_agent: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
        yfinance_import_probe=lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
    )

    local = preflight["sources"]["local_fundamentals"]
    assert local["populated_revenue_row_count"] == 1
    assert local["populated_shares_row_count"] == 1
    assert local["share_count_fixable_ticker_count"] == 1
    assert local["fundamentals_fixable_ticker_count"] == 1


def test_session_source_preflight_does_not_count_partial_local_fundamentals_as_fixable(tmp_path: Path):
    _write_fundamentals(
        tmp_path,
        [
            {
                "ticker": "ABCL",
                "source": "sec_companyfacts",
                "free_cash_flow": -174067000.0,
                "shares_outstanding": 305375393.0,
            },
            {
                "ticker": "READY",
                "source": "reviewed_manual",
                "revenue": 100.0,
                "free_cash_flow": 20.0,
                "fcf_margin": 0.2,
            },
        ],
    )
    (tmp_path / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "reports" / "ticker_readiness_report.csv").write_text(
        "\n".join(
            [
                "ticker,missing_data",
                'ABCL,"dcf: revenue, fcf_margin"',
                'READY,"dcf: revenue, free cash flow, fcf_margin"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    preflight = build_session_source_preflight(
        tmp_path,
        sec_probe=lambda _user_agent: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
        yfinance_import_probe=lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
    )

    local = preflight["sources"]["local_fundamentals"]
    assert local["fundamentals_fixable_ticker_count"] == 1
    assert preflight["preferred_lane_order"][0] == "local_reviewed_fundamentals_share_count"


def test_session_source_preflight_pivots_to_peer_lane_when_no_source_path_is_available(tmp_path: Path):
    def sec_probe(_user_agent: str) -> dict[str, object]:
        return {
            "status": "unavailable",
            "reason_code": "missing_user_agent",
            "detail": "SEC_USER_AGENT is not configured.",
            "next_action": "export SEC_USER_AGENT='Name email@example.com'",
        }

    def yfinance_import_probe() -> dict[str, object]:
        return {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        }

    preflight = build_session_source_preflight(
        tmp_path,
        sec_probe=sec_probe,
        yfinance_import_probe=yfinance_import_probe,
    )

    assert preflight["preferred_lane_order"][0] == "peer_mapping_proof"
    assert preflight["sources"]["local_fundamentals"]["status"] == "missing_file"
    rendered = render_session_source_preflight(preflight)
    assert "python3 -m pip install -e '.[research]'" in rendered
    assert "peer_mapping_proof" in rendered


def test_session_source_preflight_prefers_fmp_when_sec_and_yfinance_are_unavailable(tmp_path: Path):
    preflight = build_session_source_preflight(
        tmp_path,
        sec_probe=lambda _user_agent: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
        yfinance_import_probe=lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
        fmp_key_probe=lambda: {
            "status": "available",
            "reason_code": "configured",
            "detail": "FMP_API_KEY is configured.",
            "next_action": "",
        },
        alpha_vantage_key_probe=lambda: {
            "status": "unavailable",
            "reason_code": "provider_key_missing",
            "detail": "ALPHA_VANTAGE_API_KEY is not configured.",
            "next_action": "Set ALPHA_VANTAGE_API_KEY to enable this fallback.",
        },
    )

    assert preflight["preferred_lane_order"][0] == "fmp_fundamentals_share_count"
    assert "fmp_fundamentals_share_count" in preflight["available_lanes"]
    assert preflight["sources"]["fmp"]["status"] == "available"
    assert "fmp_fundamentals" not in preflight["do_not_retry_paths"]
    rendered = render_session_source_preflight(preflight)
    assert "- fmp: status=available reason=configured" in rendered


def test_session_source_preflight_provider_key_message_mentions_price_fallback(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "demo")

    status = probe_fmp_key()

    assert status["status"] == "available"
    assert "price fallback" in status["detail"]


def test_session_source_preflight_finnhub_key_message_mentions_price_fallback(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "demo")

    status = probe_finnhub_key()

    assert status["status"] == "available"
    assert "price fallback" in status["detail"]


def test_session_source_preflight_reports_price_ladder_keyed_fallbacks(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.setenv("FMP_API_KEY", "fmp-demo")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-demo")

    preflight = build_session_source_preflight(
        tmp_path,
        sec_probe=lambda _user_agent: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
        yfinance_import_probe=lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
    )

    price_ladder = preflight["sources"]["price_ladder"]

    assert price_ladder["status"] == "available"
    assert price_ladder["reason_code"] == "configured_keyed_fallbacks"
    assert price_ladder["provider_order"] == ["yahoo", "stooq", "fmp", "alpha_vantage", "finnhub"]
    assert price_ladder["configured_keyed_providers"] == ["fmp", "finnhub"]
    assert price_ladder["missing_keyed_provider_envs"] == ["STOOQ_API_KEY", "ALPHA_VANTAGE_API_KEY"]
    assert "price_coverage_provider_ladder" in preflight["available_lanes"]

    rendered = render_session_source_preflight(preflight)

    assert "- price_ladder: status=available reason=configured_keyed_fallbacks" in rendered
    assert "provider_order: yahoo, stooq, fmp, alpha_vantage, finnhub" in rendered
    assert "configured_price_fallbacks: fmp, finnhub" in rendered
    assert "missing_price_keys: STOOQ_API_KEY, ALPHA_VANTAGE_API_KEY" in rendered


def test_session_source_preflight_prefers_fmp_when_local_rows_do_not_fix_current_blockers(tmp_path: Path):
    _write_fundamentals(
        tmp_path,
        [
            {"ticker": "ALOY", "source": "reviewed_manual", "revenue": 123.0, "shares_outstanding": 1000.0},
        ],
    )
    (tmp_path / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "reports" / "ticker_readiness_report.csv").write_text(
        "\n".join(
            [
                "ticker,missing_data",
                "ABLV,dcf: shares_outstanding",
                "ABOS,dcf: revenue; free cash flow",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    preflight = build_session_source_preflight(
        tmp_path,
        sec_probe=lambda _user_agent: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
        yfinance_import_probe=lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
        fmp_key_probe=lambda: {
            "status": "available",
            "reason_code": "configured",
            "detail": "FMP_API_KEY is configured.",
            "next_action": "",
        },
        alpha_vantage_key_probe=lambda: {
            "status": "unavailable",
            "reason_code": "provider_key_missing",
            "detail": "ALPHA_VANTAGE_API_KEY is not configured.",
            "next_action": "Set ALPHA_VANTAGE_API_KEY to enable this fallback.",
        },
    )

    assert preflight["sources"]["local_fundamentals"]["status"] == "available"
    assert preflight["sources"]["local_fundamentals"]["share_count_fixable_ticker_count"] == 0
    assert preflight["sources"]["local_fundamentals"]["fundamentals_fixable_ticker_count"] == 0
    assert preflight["preferred_lane_order"][0] == "fmp_fundamentals_share_count"
    assert "local_reviewed_fundamentals_share_count" in preflight["available_lanes"]


def test_session_source_preflight_cli_prints_json_summary(tmp_path: Path, monkeypatch, capsys):
    _write_fundamentals(tmp_path, [{"ticker": "ALOY", "source": "reviewed_manual", "revenue": 123.0}])

    monkeypatch.setattr(
        "src.session_source_preflight.probe_sec_access",
        lambda *args, **kwargs: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
    )
    monkeypatch.setattr(
        "src.session_source_preflight.probe_yfinance_import",
        lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
    )

    argv_before = sys.argv[:]
    sys.argv = ["python", "--root", str(tmp_path), "--json"]
    try:
        main()
    finally:
        sys.argv = argv_before

    payload = json.loads(capsys.readouterr().out)
    assert payload["preferred_lane_order"][0] == "peer_mapping_proof"
    assert payload["session_flags"] == ["session_sec_unavailable", "session_yfinance_unavailable"]


def test_session_source_preflight_can_write_and_reload_session_artifact(tmp_path: Path, monkeypatch, capsys):
    _write_fundamentals(tmp_path, [{"ticker": "ALOY", "source": "reviewed_manual", "revenue": 123.0}])

    monkeypatch.setattr(
        "src.session_source_preflight.probe_sec_access",
        lambda *args, **kwargs: {
            "status": "unavailable",
            "reason_code": "network_error",
            "detail": "dns failed",
            "next_action": "Do not retry SEC-backed fundamentals in this session.",
        },
    )
    monkeypatch.setattr(
        "src.session_source_preflight.probe_yfinance_import",
        lambda: {
            "status": "unavailable",
            "reason_code": "missing_dependency",
            "detail": "No module named 'yfinance'",
            "next_action": "python3 -m pip install -e '.[research]'",
        },
    )

    argv_before = sys.argv[:]
    sys.argv = ["python", "--root", str(tmp_path), "--write-output"]
    try:
        main()
    finally:
        sys.argv = argv_before

    capsys.readouterr()
    written_path = session_source_preflight_output_path(tmp_path)
    loaded = load_session_source_preflight(tmp_path)

    assert written_path.exists()
    assert loaded is not None
    assert loaded["preferred_lane_order"][0] == "peer_mapping_proof"
    assert loaded["session_flags"] == ["session_sec_unavailable", "session_yfinance_unavailable"]
