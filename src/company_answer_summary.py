"""Read-only first-screen answers from the existing Workbench observations."""

from collections.abc import Mapping
from html import escape
import re

from src.company_sec_online_preview import _iso_date
from src.online_company_identity import _mode_reason, validated_price_filing_association
from src.online_company_prices import price_source_url
from src.online_history_contract import validated_annual_history
from src.online_peer_valuation import FISCAL_WINDOW_DAYS, MIN_PEERS
from src.online_peer_valuation_ui import _link, _multiple, _number, _reason
from src.online_research_history_view import validated_online_price_history
from src.sec_quarterly_history import validated_quarterly_history


COMPANY_ANSWERS_STYLE = """
.company-answer-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0;min-width:0}
.company-answer-summary .company-answer{min-width:0;padding:12px 14px;background:#fff;color:#172522;border:1px solid #dce3de;border-radius:8px;overflow-wrap:anywhere}
.company-answer-summary .company-answer h2{margin:0 0 4px!important;padding:0!important;font-size:.88rem!important;line-height:1.35;color:#42564e}
.company-answer-summary .company-answer p{margin:0 0 4px;line-height:1.4}
.company-answer-summary .company-answer-value{font-size:1.1rem;font-weight:750}
.company-answer-summary .company-answer-context{font-size:.82rem;color:#42564e}
.company-answer-summary summary{display:list-item;align-content:center;width:fit-content;min-height:44px;cursor:pointer;font-size:.83rem;color:#245842}
.company-answer-summary ul{margin:4px 0 0;padding-left:20px;font-size:.83rem}
.company-answer-summary li{margin:4px 0}
.company-answer-summary a{color:#245842;text-decoration:underline}
.company-answer-summary summary:focus-visible,.company-answer-summary a:focus-visible{outline:3px solid #245842;outline-offset:2px}
@media(max-width:700px){
  .company-answer-summary{grid-template-columns:minmax(0,1fr);gap:6px;margin:10px 0}
  .company-answer-summary .company-answer{display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:8px;padding:8px 10px}
  .company-answer-summary .company-answer h2,.company-answer-summary .company-answer-value,.company-answer-summary .company-answer-context{grid-column:1}
  .company-answer-summary .company-answer details{grid-column:1/-1}
  .company-answer-summary .company-answer details:not([open]){grid-column:2;grid-row:1/4;align-self:center}
  .company-answer-summary .company-answer-value{font-size:1rem}
}
@media(max-width:300px){.company-answer-summary .company-answer{display:block}}
@media(forced-colors:active){.company-answer-summary summary:focus-visible,.company-answer-summary a:focus-visible{outline-color:Highlight}}
"""

_TITLES = {'price': '最近收盘', 'financial': '财报变化', 'valuation': '同行估值'}
_GAP_VALUES = {'price': '收盘价待核对', 'financial': '财报变化待核对', 'valuation': '同行估值暂无法比较'}
_PRICE_GAPS = {
    'price_source_unavailable': '报价来源暂不可用',
    'no_completed_daily_prices': '未取得已完成的日线收盘价',
    'price_symbol_or_security_type_mismatch': '报价代码或证券类型未通过核对',
    'unsupported_price_currency': '报价币种未通过核对',
}
_FINANCIAL_GAPS = {
    'sec_user_agent_required': 'SEC 查询缺少访问标识。',
    'sec_fetch_unavailable': 'SEC 财报来源暂不可用。',
}


def _card(key, value, context, evidence=(), links=()):
    return dict(key=key, title=_TITLES[key], value=value, context=context, evidence=evidence, links=links)


def _price_answer(ticker, prices, association):
    price = validated_online_price_history(prices, ticker=ticker)
    if price is None:
        source = prices if isinstance(prices, Mapping) else {}
        if source.get('status') in {None, 'not_requested'}:
            return _card('price', '尚未查询收盘价', '使用「更新财报与价格」取得观察。',
                         ('查询后显示已完成的日线收盘价及交易日。',))
        reason = _PRICE_GAPS.get(source.get('reason'))
        links = (('Yahoo 日线查询', price_source_url(ticker.replace('.', '-'))),) if reason and source.get('ticker') == ticker else ()
        reason = reason or '收盘价来源尚未通过核对'
        return _card('price', _GAP_VALUES['price'], reason, (reason,), links)
    bar = price['bars'][-1]
    listing = validated_price_filing_association(association)
    matched = listing and listing['ticker'] == ticker and all(
        listing['source_receipts'][1].get(key) == price.get(key) for key in ('observed_at', 'payload_sha256'))
    scope = '报价场所与上市记录已核对。' if matched else '报价代码已核对，上市关联仍单独核查。'
    status = '日期过旧，近期收盘待核对' if price.get('observation_state') == 'stale_observation' else '已完成收盘'
    return _card('price', f"{price['currency']} {bar['close']:,.2f}", f"{bar['date']} · {status}",
                 (f"观察时间 {price['observed_at']} · 供应商代码 {price['provider_symbol']}", scope,
                  '历史收盘观察。拆股及股息调整口径单独核对。'),
                 (('Yahoo 日线来源', price['source_url']),))


def _comparable_revenue(financial, period, kind):
    if kind == 'annual':
        history = validated_annual_history(financial) if financial.get('status') == 'inspection_only' else None
        if history:
            for comparison in history['comparisons']:
                if comparison['to_period'] == period and comparison['status'] == 'comparable':
                    prior = next(row for row in history['periods'] if row['period_end'] == comparison['from_period'])
                    return '较上财年', comparison['direction'], prior['period_end'], prior['revenue']
    if kind != 'quarterly':
        return None
    history = validated_quarterly_history(financial)
    if not history:
        return None
    periods = history['periods']
    current = next((row for row in periods if row['period_end'] == period and row['status'] == 'available'), None)
    if current is None:
        return None
    start, end = _iso_date(current['period_start']), _iso_date(period)
    matches = []
    for row in periods:
        if row['status'] != 'available':
            continue
        prior_start, prior_end = _iso_date(row['period_start']), _iso_date(row['period_end'])
        if (351 <= (start - prior_start).days <= 379 and 351 <= (end - prior_end).days <= 379
            and abs((end - start).days - (prior_end - prior_start).days) <= 14):
            matches.append(row)
    if len(matches) != 1:
        return None
    prior = matches[0]
    latest_value, prior_value = current['fields']['revenue']['value'], prior['fields']['revenue']['value']
    direction = 'increased' if latest_value > prior_value else 'decreased' if latest_value < prior_value else 'unchanged'
    return '较上年同期', direction, prior['period_end'], prior_value


def _money(currency, value):
    if abs(value) >= 1e8:
        return f'{currency} {value / 1e8:,.2f} 亿'
    if abs(value) >= 1e4:
        return f'{currency} {value / 1e4:,.2f} 万'
    return f'{currency} {value:,.0f}' if value % 1 == 0 else f'{currency} {value:,.2f}'


def _financial_answer(projection, financial):
    financial = financial if isinstance(financial, Mapping) else {}
    fact = projection.get('facts', {}).get('revenue')
    if not fact:
        if financial.get('status') in {None, 'not_requested'}:
            message = '尚未查询财报。使用「更新财报与价格」取得可核对期间。'
        else:
            message = _FINANCIAL_GAPS.get(financial.get('reason'), '已请求数据，尚无通过核对的财报收入。')
        return _card('financial', _GAP_VALUES['financial'], message, (message,))
    start, end, kind = (projection[key] for key in ('period_start', 'period_end', 'period_kind'))
    unit, value = fact['unit'], fact['value']
    observed = fact.get('observed_at') or fact.get('observed_at_utc')
    accession = fact.get('accession')
    evidence = [f"{'直接季度' if kind == 'quarterly' else '报告年度'} {start} 至 {end} · {unit} {value:,}",
                f"字段 {fact.get('taxonomy', '')}:{fact.get('concept', '')}",
                f"申报 {accession or '未取得'} · 观察 {observed or '未取得'}"]
    filed = projection.get('filed') or fact.get('filed')
    if _iso_date(filed):
        evidence.append(f'申报日期 {filed}')
    links = [('SEC 财报字段', fact['source_ref'])] if fact.get('source_ref') else []
    cik = financial.get('sec_cik')
    if isinstance(cik, str) and re.fullmatch(r'\d{10}', cik) and isinstance(accession, str) and re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
        links.append(('SEC 申报详情', f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{accession}-index.htm'))
    comparison = _comparable_revenue(financial, end, kind)
    context = f'截至 {end}'
    if comparison:
        basis, direction, prior_date, prior_value = comparison
        direction_label = {'increased': '增加', 'decreased': '减少', 'unchanged': '持平'}
        context += f' · {basis}{direction_label[direction]}'
        evidence.append(f'对照期截至 {prior_date} · {unit} {prior_value:,}。当前仅显示变化方向。')
    else:
        context += ' · 可比变化待核对'
        evidence.append('可比基期或比较口径尚未通过核对。')
    if projection.get('withheld_periods'):
        context += ' · 较新期间待核对'
        evidence.extend(f"较新期间截至 {row['period_end']}，详情见数据来源。" for row in projection['withheld_periods'])
    label = '扣除利息费用后营收' if fact.get('concept') == 'RevenuesNetOfInterestExpense' else '营收'
    return _card('financial', f'{label} {_money(unit, value)}', context, tuple(evidence), tuple(links))


def _annual_filing_links(label, context):
    if not isinstance(context, Mapping):
        return []
    return [
        (f"{label} {row['form']}（申报记录）", row['source_ref'])
        for row in context.get('annual_versions', ())
        if isinstance(row, Mapping) and row.get('form') and row.get('source_ref')
    ]


def _valuation_answer(ticker, view):
    method = f'已披露年度摊薄 P/E · 同日收盘 · 财年窗口 {FISCAL_WINDOW_DAYS} 天 · 至少 {MIN_PEERS} 家'
    if not isinstance(view, Mapping) or view.get('status') == 'not_requested':
        return _card('valuation', '同行估值未核查', '在「估值与同行」发起核查。', (method,))
    if view.get('ticker') != ticker:
        return _card('valuation', _GAP_VALUES['valuation'], '未取得该证券的同行观察。', (method,))
    subject = view.get('subject')
    subject = subject if isinstance(subject, Mapping) and subject.get('ticker') == ticker else {}
    day = subject.get('price_date')
    peers = view.get('peers')
    peers = peers if isinstance(peers, list) else []
    count = view.get('peer_count')
    valid_count = type(count) is int and count == len(peers) and all(isinstance(row, Mapping) for row in peers)
    context_parts = [f'{day} 收盘'] if _iso_date(day) else []
    checked = view.get('checked_candidate_count')
    if type(checked) is int and checked >= 0:
        context_parts.append(f'{checked} 家已核查')
    if subject and valid_count:
        context_parts.append(f'{count} 家合格')
    evidence = [method]
    links = [('同行候选组来源', view['industry_source_ref'])] if view.get('industry_source_ref') else []
    for label, key in (('本公司年度申报', 'filing_ref'), ('本公司价格来源', 'price_source_ref')):
        if subject.get(key):
            links.append((label, subject[key]))
    if not subject:
        source = view.get('subject_source_context')
        links.extend(_annual_filing_links('本公司', source))
        dates = source.get('close_date_observation') if isinstance(source, Mapping) else None
        if isinstance(dates, Mapping) and _iso_date(dates.get('quote_day')) and _iso_date(dates.get('close_day')):
            evidence.append(f"供应商报价日期 {dates['quote_day']} · 日线收盘 {dates['close_day']}。")
            for label, key in (('本公司供应商报价来源', 'quote_source_ref'), ('本公司日线来源', 'close_source_ref')):
                if dates.get(key):
                    links.append((label, dates[key]))
        listing = view.get('listing_context')
        if isinstance(listing, Mapping) and view.get('reason') in {
            'listing_classification_unavailable', 'selected_listing_or_cik_unverified',
        }:
            for label, key in (('上市来源查询', 'source_attempts'), ('上市核对来源', 'source_receipts')):
                links.extend((label, row['source_url']) for row in listing.get(key, ())
                             if isinstance(row, Mapping) and row.get('source_url'))
    amendment = subject.get('amendment_scope')
    if isinstance(amendment, Mapping) and amendment.get('status') == 'supported':
        receipts = amendment.get('source_receipts', ())
        if len(receipts) == 2 and isinstance(receipts[1], Mapping) and receipts[1].get('source_url'):
            links.append(('本公司年度申报修订原文', receipts[1]['source_url']))
    if subject and _number(subject.get('multiple')) and subject['multiple'] > 0:
        evidence.append(f"本公司年度 P/E {_multiple(subject['multiple'])}。")
    supported = (
        view.get('status') == 'research_comparison' and view.get('metric') == 'reported_annual_diluted_pe'
        and _iso_date(day) and valid_count and count >= MIN_PEERS
        and all(isinstance(row.get('ticker'), str) and row.get('price_date') == day for row in peers)
        and _number(subject.get('multiple')) and subject['multiple'] > 0
        and _number(view.get('peer_median')) and view['peer_median'] > 0 and _number(view.get('premium_fraction'))
    )
    if supported:
        premium = view['premium_fraction']
        magnitude = f'{abs(premium) * 100:.1f}%' if abs(premium) >= .0005 else '<0.1%'
        value = ('年度 P/E 等于同行参照' if premium == 0 else
                 f"年度 P/E {'高于' if premium > 0 else '低于'}同行参照 {magnitude}")
        evidence.append(f"同行参照中位数 {_multiple(view['peer_median'])} · " + '、'.join(row['ticker'] for row in peers))
        for peer in peers:
            for label, key in (('年度申报', 'filing_ref'), ('日线来源', 'price_source_ref')):
                if peer.get(key):
                    links.append((f"{peer['ticker']} {label}", peer[key]))
    else:
        reason = _reason(view.get('reason'))
        if view.get('status') == 'research_comparison':
            reason = '同行数量、倍数或同日收盘证据尚未通过核对。'
        value = _GAP_VALUES['valuation']
        if not subject or not context_parts:
            context_parts.append(reason)
        evidence.append(reason)
        if not subject:
            evidence.append('本公司依据未通过核对，同行尚未核查。')
    for row in view.get('excluded') or ():
        if not isinstance(row, Mapping) or not row.get('ticker'):
            continue
        symbol = row['ticker']
        evidence.append(f"{symbol} · {_reason(row.get('reason'))}")
        diagnostics = row.get('diagnostics')
        if not isinstance(diagnostics, Mapping):
            continue
        eps = diagnostics.get('annual_eps_observation')
        if isinstance(eps, Mapping) and eps.get('filing_ref'):
            links.append((f'{symbol} 年度申报（未纳入）', eps['filing_ref']))
        else:
            links.extend(_annual_filing_links(symbol, diagnostics))
        price = diagnostics.get('price_observation')
        if isinstance(price, Mapping) and price.get('source_ref'):
            links.append((f'{symbol} 日线来源（未纳入）', price['source_ref']))
        audit = diagnostics.get('annual_eps_audit')
        if isinstance(audit, Mapping) and audit.get('source_url'):
            links.append((f'{symbol} 年度 EPS 原文', audit['source_url']))
    return _card('valuation', value, ' · '.join(context_parts), tuple(evidence), tuple(links))


def build_company_answers(ticker, projection, financial, prices, association, peer_view):
    """Return display cards without fetching data or changing saved research."""
    if _mode_reason('research') or projection.get('identity_conflict'):
        reason = '公司或证券身份冲突，暂不展示数值。' if projection.get('identity_conflict') else '当前工作区不可使用个人研究观察。'
        return tuple(_card(key, _GAP_VALUES[key], reason, (reason,)) for key in _TITLES)
    return (_price_answer(ticker, prices, association), _financial_answer(projection, financial),
            _valuation_answer(ticker, peer_view))


def company_answers_html(answers):
    """Render escaped cards and native evidence disclosures in both surfaces."""
    cards = []
    for answer in answers:
        title, value, context = (escape(answer[key]) for key in ('title', 'value', 'context'))
        lines = ''.join(f'<li>{escape(line)}</li>' for line in answer['evidence'])
        links = ''.join(f'<li>{_link(url, label)}</li>' for label, url in answer.get('links', ()))
        cards.append(
            f'<article class="company-answer" data-company-answer="{escape(answer["key"], quote=True)}">'
            f'<h2>{title}</h2><p class="company-answer-value">{value}</p>'
            f'<p class="company-answer-context">{context}</p>'
            f'<details><summary>查看{title}依据</summary><ul>{lines}{links}</ul></details></article>'
        )
    return '<section class="company-answer-summary" aria-label="公司研究摘要">' + ''.join(cards) + '</section>'
