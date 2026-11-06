"""The Discover report exposes each lane and its original source scope."""

import re

import pytest
from streamlit.testing.v1 import AppTest

from src.online_us_universe import SOURCE_URLS


def _group(label, denominator, counts, *, sic=None):
    lanes = {}
    for name, (available, unprobed, reasons) in counts.items():
        lanes[name] = {
            "available": available,
            "failed": sum(reasons.values()),
            "unprobed": unprobed,
            "reasons": reasons,
        }
    return {"sic": sic, "label": label, "denominator": denominator, "lanes": lanes}


@pytest.fixture
def report():
    no_route = {"no_unambiguous_sec_search_route": 1}
    no_identity = {"issuer_source_unavailable": 1}
    no_revenue = {"latest_reported_quarter_not_covered": 2}
    no_price = {"price_source_unavailable": 2}
    eps_conflict = "annual_eps_conflict"
    total = _group("All issuer candidates", 11, {
        "search": (10, 0, no_route),
        "identity": (8, 2, no_identity),
        "financial": (7, 2, no_revenue),
        "price": (4, 5, no_price),
        "peer": (2, 6, {eps_conflict: 3}),
    })
    known = _group("Semiconductors", 7, {
        "search": (7, 0, {}),
        "identity": (7, 0, {}),
        "financial": (7, 0, {}),
        "price": (4, 1, no_price),
        "peer": (2, 3, {eps_conflict: 2}),
    }, sic="3674")
    unknown = _group("Unknown SIC", 4, {
        "search": (3, 0, no_route),
        "identity": (1, 2, no_identity),
        "financial": (0, 2, no_revenue),
        "price": (0, 4, {}),
        "peer": (0, 3, {eps_conflict: 1}),
    })
    start, end = "2026-11-05T19:00:00Z", "2026-11-05T19:01:00Z"
    return {
        "total": total,
        "groups": [known, unknown],
        "scope": {
            "observed_from": start,
            "observed_to": end,
            "latest_evidence_at": "2026-11-05T19:03:00Z",
            "inventory_count": 20,
            "known_etf_count": 2,
            "unmatched_listing_count": 3,
            "outside_queue_cik_count": 2,
            "sec_exchange_only_count": 5,
            "otc_excluded_count": 9,
            "null_exchange_excluded_count": 4,
            "test_issues_excluded_count": 7,
            "venue_gaps": ["TXSE", "Unresolved code F"],
            "price_dates": ["2026-11-03", "2026-11-04"],
            "source_receipts": [
                {"source_url": url, "observed_at": start, "payload_sha256": "a" * 64}
                for url in SOURCE_URLS
            ],
        },
        "peer_sample_size": 15,
    }


def _app():
    import streamlit as st
    from src.online_industry_coverage_ui import render_industry_coverage

    render_industry_coverage(st, st.session_state.get("fixture_coverage_report"))


def _text(app):
    return "\n".join(item.value for item in [*app.markdown, *app.caption])


def test_coverage_prompts_for_an_inventory_without_showing_empty_lane_counts():
    app = AppTest.from_function(_app).run()

    assert not app.exception
    assert "Issuer coverage by industry" in _text(app)
    assert "Load U.S. listing inventory" in app.info[0].value
    assert not app.selectbox
    assert not re.search(r"\d+\s*/\s*\d+", _text(app))


def test_coverage_renders_five_lane_counts_and_all_four_dated_inventory_links(report):
    app = AppTest.from_function(_app)
    app.session_state["fixture_coverage_report"] = report
    app.run()

    assert not app.exception
    text = _text(app)
    assert re.findall(r"\b(\d+)\s*/\s*(11)\b", text) == [
        ("10", "11"), ("8", "11"), ("7", "11"), ("4", "11"), ("2", "11"),
    ]
    assert re.findall(r"\b(\d+)\s*已核查", text) == ["1", "1", "2", "2", "3"]
    assert re.findall(r"\b(\d+)\s*未核查", text) == ["0", "2", "2", "5", "6"]
    assert re.search(r"冲突[^\n]*\b3\b", text)
    assert "2026-11-05T19:00:00Z" in text and "2026-11-05T19:01:00Z" in text
    assert "2026-11-05T19:03:00Z" in text
    assert "2026-11-03" in text and "2026-11-04" in text
    assert "TXSE" in text and "Unresolved code F" in text
    for url in SOURCE_URLS:
        assert f"]({url})" in text


def test_selecting_unknown_sic_shows_its_own_denominator_and_reasons(report):
    app = AppTest.from_function(_app)
    app.session_state["fixture_coverage_report"] = report
    app.run()

    group = app.selectbox(key="online-industry-coverage-group")
    assert "Unknown SIC" in group.options
    group.select("Unknown SIC").run()

    assert not app.exception
    text = _text(app)
    assert re.findall(r"\b(\d+)\s*/\s*(4)\b", text) == [
        ("3", "4"), ("1", "4"), ("0", "4"), ("0", "4"), ("0", "4"),
    ]
    assert re.search(r"冲突[^\n]*\b1\b", text)
    assert not re.search(r"\b10\s*/\s*11\b", text)


def test_sample_shows_checked_and_pending_separately_from_the_sic_population(report):
    from src.online_peer_sec_cofiling import ARCHIVE_URLS

    cohort = _group("公用事业", 3, {
        "price": (1, 2, {}),
        "peer": (0, 1, {"multiple_issuer_share_classes_unresolved": 1,
                        "at_least_three_compatible_industry_references_required": 1}),
    })
    cohort["members"] = [
        dict(ticker="DUK", scope_matched=True, sic="4931", price=True, price_date="2026-11-05",
             peer="multiple_issuer_share_classes_unresolved"),
        dict(ticker="SO", scope_matched=True, sic="4911", price=None,
             peer="at_least_three_compatible_industry_references_required", peer_count=0, peer_date="2026-11-05",
             peer_references_partial=True,
             cofiling_documents=[dict(source_url=url) for url in ARCHIVE_URLS],
             annual_common_filing=dict(period_end="2025-12-31",
                 source_ref="https://www.sec.gov/Archives/edgar/data/92122/000009212226000006/so-20251231.htm")),
        dict(ticker="NEE", scope_matched=False, price=None, peer=None),
    ]
    report["representative_groups"] = [cohort]
    app = AppTest.from_function(_app)
    app.session_state["fixture_coverage_report"] = report
    app.run()

    assert not app.exception
    text = _text(app)
    assert "公用事业 · DUK、SO、NEE" in text
    assert "收盘价** · 已核查 1 / 3 · 通过 1 / 3 · 有缺口 0 · 待核查 2" in text
    assert "同行估值** · 已核查 2 / 3 · 通过 0 / 3 · 有缺口 2 · 待核查 1" in text
    assert "SIC 4931 · 收盘价 2026-11-05" in text
    assert "所选证券的每股收益口径尚未核对" in text
    assert "0 家合格同行 · 参照核查未完成 · 2026-11-05" in text
    assert "[10-K 普通股摊薄 EPS 原文（2025-12-31）](https://www.sec.gov/Archives/edgar/data/92122/" in text
    assert f"[10-Q 身份依据（母公司）]({ARCHIVE_URLS[0]})" in text
    assert f"[联报公司副本]({ARCHIVE_URLS[1]})" in text
    assert "NEE** · 本次目录缺少唯一的代表代码与发行人关联" in text


def test_qcom_representative_row_distinguishes_candidate_checks_from_pending(report):
    cohort = _group("半导体", 3, {
        "price": (0, 3, {}),
        "peer": (0, 2, {"at_least_three_compatible_industry_references_required": 1}),
    })
    cohort["members"] = [
        dict(ticker="AMD", scope_matched=False, price=None, peer=None),
        dict(ticker="TXN", scope_matched=False, price=None, peer=None),
        dict(ticker="QCOM", scope_matched=True, sic="3663", price=None,
             peer="at_least_three_compatible_industry_references_required",
             candidate_basis="reviewed_qcom_sec_sic_3663", candidate_count=3,
             checked_candidate_count=1, pending_candidate_count=2,
             excluded=[
                 {"ticker": "UI", "reason": "provider_industry_differs"},
                 {"ticker": "MSI", "reason": "source_paused_after_repeated_failures"},
                 {"ticker": "HLIT", "reason": "peer_not_collected"},
             ]),
    ]
    report["representative_groups"] = [cohort]
    app = AppTest.from_function(_app)
    app.session_state["fixture_coverage_report"] = report
    app.run()

    assert not app.exception
    text = _text(app)
    assert "SEC SIC 3663 候选 · 候选已核查 1 / 3 · 候选待核查 2 家" in text
    assert "UI** · 未通过 · 供应商行业分类不同" in text
    assert "MSI** · 待核查 · 连续来源失败" in text
    assert "HLIT** · 待核查 · 尚未取得" in text
    assert "同行估值** · 已核查 1 / 3 · 通过 0 / 3" in text
