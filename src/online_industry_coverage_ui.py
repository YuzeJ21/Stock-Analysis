"""Read-only Discover view of the observed issuer coverage report."""

from src.online_peer_coverage_ui import qcom_candidate_display
from src.online_peer_valuation_ui import REASONS as PEER_REASONS
from src.online_us_universe import SOURCE_URLS


_LANES = {
    "search": ("SEC 搜索可找到", "带日期的 SEC 搜索目录中，至少一个符合队列条件的代码唯一匹配该发行人的 CIK。"),
    "identity": ("财报发行人身份已核对", "Companyfacts 与包含当前代表代码的 SEC submissions 核对为同一 CIK。"),
    "financial": ("最新申报收入可核对", "至少一个最新年度、直接季度或中期申报期间有可追溯的收入字段。"),
    "price": ("有带日期的收盘价", "代表代码与场所匹配，并有最近七天内已收盘的日线。价格来源不提供独立 CIK 核对。"),
    "peer": ("同口径同行估值可用", "本公司与至少三家同行通过同日收盘价、年度摊薄每股收益、币种和证券口径的 P/E 比较规则。"),
}
_SOURCE_LABELS = dict(zip(SOURCE_URLS, (
    "Nasdaq Trader — Nasdaq-listed securities",
    "Nasdaq Trader — other listed securities",
    "SEC — company ticker directory",
    "SEC — company ticker and exchange directory",
)))
_COVERAGE_REASONS = {
    **PEER_REASONS,
    "no_unambiguous_sec_search_route": "SEC 搜索目录中未找到符合条件的代码与 CIK 的唯一匹配。",
    "sec_facts_or_issuer_match_unavailable": "SEC Companyfacts 暂不可用或未匹配发行人。",
    "sec_profile_schema_invalid": "SEC submissions 的资料结构未通过核对。",
    "industry_ticker_mismatch": "SEC submissions 未列出对应的代表代码。",
    "invalid_preview": "SEC 财报来源或来源校验未通过。",
    "invalid_annual_source_anchor": "年度字段无法绑定申报来源。",
    "supported_direct_quarter_revenue_unavailable": "缺少可核对的直接季度收入。",
    "annual_evidence_unavailable": "年度财报证据不可用。",
    "latest_reported_annual_not_covered": "尚未覆盖最新年度。",
    "latest_reported_quarter_not_covered": "尚未覆盖最新季度。",
    "latest_reported_quarter_revenue_unavailable": "最新季度收入不可用。",
    "latest_reported_foreign_revenue_unavailable": "最新外国发行人收入不可用。",
    "peer_issuer_mismatch": "同行核查记录的发行人 CIK 与本目录不同。",
    "peer_sec_sic_mismatch": "同行核查中的 SEC 行业与发行人行业证据不一致。",
    "price_source_unavailable": "日线价格来源暂不可用。",
    "no_recent_completed_price": "未找到最近七天内已完成的收盘价。",
    "price_exchange_mismatch": "报价来源的交易所与目录不一致。",
    "price_symbol_or_security_type_mismatch": "报价代码或证券类型与目录不一致。",
    "price_evidence_unverified": "日线价格来源未通过验证。",
}
_ALL = "All issuer candidates"


def _reason_text(reason):
    return ' / '.join(_COVERAGE_REASONS.get(part, part.replace('_', ' ')) for part in reason.split(' / '))


def _sample_lane(counts, denominator):
    checked = counts['available'] + counts['failed']
    return (f"已核查 {checked} / {denominator} · 通过 {counts['available']} / {denominator}"
            f" · 有缺口 {counts['failed']} · 待核查 {counts['unprobed']}")


def _render_representatives(st, groups):
    if not groups:
        return
    st.markdown("### 三行业代表样本")
    st.caption("按预先选定的研究行业统计，每组分母为 3 家。下方逐家显示已核实的 SEC SIC。"
               "价格和同行分别核查。同行估值仍要求同日收盘价和可比的年度摊薄每股收益。")
    for group in groups:
        lanes = group['lanes']
        n = group['denominator']
        tickers = '、'.join(member['ticker'] for member in group['members'])
        st.markdown(f"**{group['label']} · {tickers}**\n\n"
                    f"- **收盘价** · {_sample_lane(lanes['price'], n)}\n"
                    f"- **同行估值** · {_sample_lane(lanes['peer'], n)}")
    with st.expander("逐家查看价格、估值与缺口", expanded=False):
        for group in groups:
            st.markdown(f"**{group['label']}**")
            for member in group['members']:
                ticker = member['ticker']
                if not member['scope_matched']:
                    st.markdown(f"- **{ticker}** · 本次目录缺少唯一的代表代码与发行人关联，两项待核查。")
                    continue
                price, peer = member['price'], member['peer']
                price_text = member['price_date'] if price is True else _reason_text(price) if price else '待核查'
                peer_text = _reason_text(peer) if isinstance(peer, str) else '待核查' if peer is None else ''
                if member.get('peer_count') is not None:
                    summary = f"{member['peer_count']} 家合格同行"
                    if member.get('peer_references_partial'):
                        summary += " · 参照核查未完成"
                    if member['peer_date']:
                        summary += f" · {member['peer_date']}"
                    peer_text = f"{summary} · {peer_text}" if peer_text else summary
                filing = member.get('annual_common_filing')
                filing_text = (f" · [10-K 普通股摊薄 EPS 原文（{filing['period_end']}）]({filing['source_ref']})"
                               if filing else '')
                cofiling = member.get('cofiling_documents')
                if cofiling and len(cofiling) == 2:
                    parent, co_registrant = cofiling
                    filing_text += (f" · [10-Q 身份依据（母公司）]({parent['source_url']})"
                                    f" · [联报公司副本]({co_registrant['source_url']})")
                sic = f"SIC {member['sic']}" if member['sic'] else 'SEC 行业待核查'
                line = f"- **{ticker}** · {sic} · 收盘价 {price_text} · 同行估值 {peer_text}{filing_text}"
                if candidates := qcom_candidate_display(member):
                    progress, outcomes = candidates
                    line += f" · {progress}"
                    if outcomes:
                        for symbol, reason, links in outcomes:
                            line += f"\n  - **{symbol}** · {reason}"
                            for url, label in links:
                                line += f" · [{label}]({url})"
                st.markdown(line)
    st.caption("使用下方的单公司价格表单，或在上方「同行估值覆盖 · 行业样本」选择待核查公司。")


def render_industry_coverage(st, report):
    """Show five independent lanes for the selected issuer group without fetching."""
    st.markdown("### Issuer coverage by industry")
    if report is None:
        st.info("Load U.S. listing inventory 或恢复已保存的覆盖进度，再查看分行业的发行人证据。")
        return

    total, scope = report["total"], report["scope"]
    st.caption(
        f"上市目录观察时间 {scope['observed_from']} 至 {scope['observed_to']}（UTC）。"
        f"覆盖范围为这份目录中的 {total['denominator']:,} 个发行人候选；同一 CIK 的不同股类仅计一次。"
        "各指标独立核查，分母为所选组的全部发行人候选。"
    )
    choices = {_ALL: total}
    for group in report["groups"]:
        choices[group["label"]] = group
    selected = st.selectbox("Industry (SEC SIC)", tuple(choices), key="online-industry-coverage-group")
    summary = choices[selected]
    denominator = summary["denominator"]
    lines = []
    for lane, (label, _) in _LANES.items():
        counts = summary["lanes"][lane]
        share = f" ({100 * counts['available'] / denominator:.1f}%)" if denominator else ""
        lines.append(
            f"- **{label}** · **{counts['available']:,} / {denominator:,}**{share} 可用"
            f" · {counts['failed']:,} 已核查但不可用 · {counts['unprobed']:,} 未核查"
        )
    st.markdown("\n".join(lines))
    st.caption(f"同行结果来自「同行估值覆盖 · 行业样本」的 {report['peer_sample_size']:,} 个指定代码。"
               "其余发行人留在分母中。价格和同行检查仅在当前会话保留。"
               "未知 SIC 包括行业证据不足或尚未核查的发行人。")
    price_dates = scope.get("price_dates", [])
    if price_dates:
        date_range = price_dates[0] if len(price_dates) == 1 else f"{price_dates[0]} 至 {price_dates[-1]}"
        st.caption(f"全目录已核对的日线收盘日期为 {date_range}。这是有日期的历史价格观察。")

    with st.expander("Coverage rules, gaps and sources", expanded=False):
        st.markdown("**所选行业的核查规则与缺口**")
        for lane, (label, definition) in _LANES.items():
            reasons = summary["lanes"][lane]["reasons"]
            details = "\n".join(
                f"- {_reason_text(reason)} · {count:,}"
                for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))
            )
            st.markdown(f"**{label}**  \n{definition}\n\n" + (details or "本组无已记录的缺口原因。"))

        st.markdown(
            "**目录范围**\n\n"
            f"- {scope['inventory_count']:,} 条观察到的上市记录，其中 {scope['known_etf_count']:,} 条为已知 ETF，"
            f"{scope['unmatched_listing_count']:,} 条未匹配 CIK，{scope['sec_exchange_only_count']:,} 条来自 SEC 交易所目录补充。\n"
            f"- {scope['outside_queue_cik_count']:,} 个已匹配 CIK 不在发行人候选队列内。\n"
            f"- 目录范围之外的记录包括 {scope['test_issues_excluded_count']:,} 条测试证券、"
            f"{scope['otc_excluded_count']:,} 条 SEC OTC 记录，以及 {scope['null_exchange_excluded_count']:,} 条 SEC 交易所缺失记录。"
        )
        if scope["venue_gaps"]:
            st.markdown("**待核对的上市场所**\n\n" + "\n".join(f"- {gap}" for gap in scope["venue_gaps"]))
        st.caption(
            f"最近纳入的观察或核查时间 {scope['latest_evidence_at']}（UTC）。"
            "价格和同行只合并目录观察开始后 24 小时内的核查。旧存档缺少搜索证明时，该项显示未核查。"
            "完整美国市场、持续或现行上市、发行人注册地、证券类别与投资分析资格需独立核对。"
            "目录与价格仅供个人研究查阅。财报字段适用各自的来源范围。"
        )
        for receipt in scope.get("source_receipts", []):
            url = receipt["source_url"]
            if url in _SOURCE_LABELS:
                st.markdown(f"- [{_SOURCE_LABELS[url]}]({url}) · {receipt['observed_at']}")
    _render_representatives(st, report.get("representative_groups"))
