"""Source-labelled personal inspection of one exact SEC primary filing."""
from html import escape
from collections.abc import Mapping

from src.online_company_identity import _mode_reason
from src.online_research_history_view import STYLE, _amount
from src.sec_exact_filing import validated_filing_preview
from src.sec_inline_filing import FIELDS,BANK_FIELDS

_STYLE=STYLE+'<style>.exact-sec-filing{margin:16px 0;padding:16px;border:1px solid #d9e0dc;border-radius:8px;min-width:0;box-sizing:border-box;overflow-wrap:anywhere}.exact-filing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,21rem),1fr));gap:12px}.exact-sec-filing article{min-width:0;box-sizing:border-box;padding:12px;border:1px solid #d9e0dc;border-radius:8px;background:white}.exact-sec-filing dl div{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px}.exact-sec-filing dd{margin:0;font-weight:650}.exact-sec-filing small{color:#52615c}</style>'
_LABELS={'revenue':'Revenue','operating_income':'Operating income','cash_from_operations':'Operating cash flow','capital_expenditures':'PP&E purchases','net_interest_income':'Net interest income','noninterest_income':'Noninterest income'}


def _label(name,field):
    concept=field.get('concept') if field else None
    if name=='revenue':
        return {'RegulatedAndUnregulatedOperatingRevenue':'Regulated and unregulated operating revenue',
            'RevenuesNetOfInterestExpense':'Revenue · net of interest expense',
            'RevenueFromContractsWithCustomers':'Revenue · customer contracts',
            'RevenueFromContractWithCustomerExcludingAssessedTax':'Revenue · customer contracts, excluding assessed tax',
            'RevenueFromContractWithCustomerIncludingAssessedTax':'Revenue · customer contracts, including assessed tax',
            'SalesRevenueNet':'Revenue · net sales','SalesRevenueGoodsNet':'Revenue · goods sales'}.get(concept,'Revenue')
    if concept=='ProfitLossFromOperatingActivities':return 'Operating profit / loss'
    if concept=='PaymentsToAcquireProductiveAssets':return 'Capital spending · productive assets'
    return _LABELS[name]+(' · continuing operations' if concept and concept.endswith('ContinuingOperations') else '')


def filing_preview_html(packet,ticker,period_kind):
    if _mode_reason('research'):return '<p>Exact filing inspection is available only in Personal Research.</p>'
    if not isinstance(packet,Mapping) or packet.get('status')=='not_requested':
        return '<p>Choose the latest quarter or annual filing, then check its direct reported fields online.</p>'
    view=validated_filing_preview(packet,ticker,period_kind)
    if view is None:
        reason=packet.get('reason','Filing evidence failed validation')
        return '<p>Exact filing evidence withheld · '+escape(str(reason).replace('_',' '))+'.</p>'
    if view.get('source_id')=='sec_archive_html_bank':return _bank_html(view)
    bank_note='<p>Bank income context: net interest income and noninterest income are direct reported components, not combined into revenue. A banking SIC observation does not establish analysis eligibility.</p>' if view.get('source_id')=='sec_archive_inline_bank' else ''
    field_names=BANK_FIELDS if view.get('source_id')=='sec_archive_inline_bank' else FIELDS
    cards=[]
    for row in view['periods']:
        title={'annual':'Annual statement','quarterly':'Direct reported quarter','cumulative':'Cumulative · not a single quarter'}[row['kind']]
        values=''.join('<div><dt>'+escape(_label(name,row['fields'].get(name)))+'</dt><dd>'
            +(escape(view['unit'])+' '+_amount(row['fields'][name]['value']) if name in row['fields'] else 'Withheld')+'</dd></div>' for name in field_names)
        evidence=''.join('<li>'+escape(name.replace('_',' '))+': '+escape(f['taxonomy']+':'+f['concept'])
            +' · context '+escape(f['context_id'])+' · unit '+escape(f['unit_id'])+' · displayed '+escape(f['raw_text'])
            +' · scale '+str(f['scale'])+' · sign '+escape(f['sign'] or 'positive')+' · decimals '+escape(f['decimals'])
            +' · <a href="'+escape(f['source_ref'],quote=True)+'" target="_blank" rel="noopener noreferrer">Source fact '+escape(f['fact_id'])+'</a></li>' for name,f in row['fields'].items())
        gaps=''.join('<li>'+escape(_LABELS[name])+': '+escape(reason.replace('_',' '))+'</li>' for name,reason in row['withheld_fields'].items())
        cards.append('<article><h4>'+title+'</h4><p>'+escape(row['period_start'])+' to '+escape(row['period_end'])+' · '+escape(view['unit'])+'</p><dl>'+values+'</dl><details><summary>Field definitions and gaps</summary><ul>'+evidence+gaps+'</ul></details></article>')
    refs=''.join('<li><a href="'+escape(r['source_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">SEC source</a> · observed '+escape(r['observed_at'])+' · SHA-256 '+escape(r['payload_sha256'])+'</li>' for r in view['source_receipts'])
    return (_STYLE+'<section class="exact-sec-filing" aria-label="Exact SEC filing"><h3>Exact SEC filing · '+escape(view['form'])+'</h3>'+bank_note+
        '<p>One issuer and one primary document. Direct amounts retain their reporting currency; missing quarters and cash flows are never inferred.</p>'
        '<div class="exact-filing-grid">'+''.join(cards)+'</div>'
        '<details><summary>Filing identity and source receipts</summary><p>SEC CIK '+escape(view['sec_cik'])+' · accession '+escape(view['accession'])
        +' · report ended '+escape(view['period_end'])+' · filed '+escape(view['filed'])+' · accepted '+escape(view['accepted_at'])+'</p><ul>'+refs+'</ul></details>'
        '<p><strong>Archive source rights:</strong> unregistered personal inspection only; commercial use and raw redistribution remain held. Companyfacts coverage and saved readiness stay separate. This is an observed filing, not point-in-time research history or valuation.</p></section>')


def _bank_html(view):
    from src.sec_html_bank import DEFINITIONS
    cards=[]
    for row in view['periods']:
        values=''.join('<div><dt>'+escape(DEFINITIONS[name][2])+'</dt><dd>'
            +('INR '+_amount(row['fields'][name]['value']) if name in row['fields'] else 'Withheld')+'</dd></div>' for name in DEFINITIONS)
        facts=''.join('<li>'+escape(f['label'])+' · reported '+escape(f['raw_text'])+' thousand INR · table '+str(f['table_index'])+', row '+str(f['row_index'])+', columns '+escape(str(f['column_span']))
            +' · <a href="'+escape(f['source_ref'],quote=True)+'" target="_blank" rel="noopener noreferrer">Statement source</a></li>' for f in row['fields'].values())
        gaps=''.join('<li>'+escape(name.replace('_',' '))+': '+escape(reason.replace('_',' '))+'</li>' for name,reason in row['withheld_fields'].items())
        cards.append('<article><h4>Annual bank statement · '+escape(row['period_end'])+'</h4><p>'+escape(row['period_start'])+' to '+escape(row['period_end'])+' · INR</p><dl>'+values+'</dl><details><summary>Reported definitions and gaps</summary><ul>'+facts+gaps+'</ul></details></article>')
    refs=''.join('<li><a href="'+escape(r['source_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">SEC source</a> · observed '+escape(r['observed_at'])+' · SHA-256 '+escape(r['payload_sha256'])+'</li>' for r in view['source_receipts'])
    registration=view['registration_observation']
    registration_html=''
    if registration['status']=='observed_as_filed':
        registration_html='<p>As-filed security disclosure · '+escape(registration['as_of'])+': American Depositary Shares; underlying equity shares are not for trading independently. Current legal security type remains unverified.</p>'
    return (_STYLE+'<section class="exact-sec-filing" aria-label="Exact SEC filing"><h3>Exact SEC filing · '+escape(view['form'])+' · Indian GAAP</h3><p>ICICI Bank consolidated annual statements. Direct source amounts in thousands of rupees are normalized to INR; purchase cash flows keep their reported negative sign.</p><div class="exact-filing-grid">'+cards[0]+'</div><details><summary>Earlier annual bank statements (2)</summary><div class="exact-filing-grid">'+''.join(cards[1:])+'</div></details><p>Generic revenue, operating income, net interest income, FCF and valuation remain withheld; bank total income retains its gross-interest definition.</p><details><summary>Filing identity and source receipts</summary><p>SEC CIK '+escape(view['sec_cik'])+' · accession '+escape(view['accession'])+' · filed '+escape(view['filed'])+' · accepted '+escape(view['accepted_at'])+'</p>'+registration_html+'<ul>'+refs+'</ul></details><p><strong>Archive source rights:</strong> unregistered personal inspection only; commercial use and raw redistribution remain held. Companyfacts coverage and saved readiness stay separate.</p></section>')
