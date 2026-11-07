"""Readable online comparison and source disclosure; no transport or state writes."""
from collections.abc import Mapping
from html import escape
import math
import re
from urllib.parse import urlsplit

from src.online_peer_valuation import FISCAL_WINDOW_DAYS, MIN_PEERS

REASONS = {
    'reported_annual_pe_industry_reference_only':'Qualified reported annual P/E industry references are available. This shows a multiple difference only.',
    'annual_filing_missing':'No annual Form 10-K or 20-F supported by this method was found.',
    'latest_annual_eps_missing_including_amendment':'The latest annual or amended filing has no matching diluted EPS. The gap remains open.',
    'annual_filing_tie_unresolved':'Multiple annual filings share a filing date, and their version order is unresolved.',
    'annual_eps_nonpositive_or_invalid':'Annual diluted EPS is zero, negative, or invalid, so P/E does not apply.',
    'annual_diluted_eps_usd_missing':'Reported annual diluted EPS in USD/shares was unavailable.',
    'annual_eps_conflict':'The same annual filing contains conflicting EPS facts.',
    'annual_eps_filing_mismatch':'The EPS fact does not match the selected filing form or publication date.',
    'annual_eps_unit_conflict':'The annual EPS facts have conflicting currencies or units.',
    'annual_period_or_publication_not_current_for_price':'The annual period is too old, or the filing was unpublished on the price date.',
    'peer_fiscal_window_differs':'Actual fiscal start or end dates differ by more than 35 days.',
    'provider_industry_differs':'Provider industry classifications differ.',
    'sec_industry_differs':'SEC industry codes differ.',
    'duplicate_peer_issuer':'This security has the same issuer as an included reference.',
    'invalid_peer_source_evidence':'Reference source evidence failed structure or content checks.',
    'post_period_split_requires_share_basis_review':'A post-period split lacks a verified EPS adjustment basis.',
    'split_history_does_not_cover_period_end':'Split history does not cover the EPS period end, so share basis remains unverified.',
    'split_evidence_invalid':'Split dates or ratios failed verification.',
    'peer_price_date_differs':'The reference closing-price date differs from the selected company date.',
    'completed_price_source_unverified':'A verified close for a completed trading day was unavailable.',
    'price_exchange_mismatch':'The daily price and provider quote have different exchanges.',
    'price_timezone_mismatch':'The daily price and provider quote have different trading time zones.',
    'quote_not_same_recent_completed_day':'The quote is not from the same recent completed trading day.',
    'quote_and_daily_close_differ':'The provider quote does not reconcile to the daily close.',
    'price_quote_chronology_invalid':'The price source was observed before its corresponding quote and is withheld.',
    'price_source_digest_missing':'The price source digest is missing.',
    'source_observation_stale_or_future':'The source observation is over 24 hours old or in the future. Refresh explicitly.',
    'vendor_filing_not_matched_to_sec':'The provider filing link did not match SEC filing metadata.',
    'vendor_filing_issuer_conflict':'The provider filing link has an issuer identity conflict.',
    'quote_identity_or_type_mismatch':'Provider symbol or security type does not match.',
    'quote_exchange_mismatch':'The provider exchange differs from the independent listing source.',
    'unsupported_quote_or_financial_currency':'Price and financial currencies do not meet the supported USD basis.',
    'peer_listing_or_share_basis_unverified':'Independent common-share listing identity remains unverified.',
    'selected_listing_or_cik_unverified':'The selected listing, CIK, or common-share type remains unverified.',
    'multiple_issuer_share_classes_unresolved':'The issuer has related symbols, and EPS basis for the selected security remains unverified.',
    'selected_common_other_security_basis_unresolved':'The selected common share has document evidence. EPS basis for other related securities remains unverified.',
    'depositary_security_requires_separate_method':'The NYSE-traded security is an ADS. EPS per ADS, currency, and conversion basis require a separate method.',
    'successor_annual_basis_unverified':'Issuer continuity evidence exists, but the current issuer annual EPS denominator remains unavailable.',
    'selected_security_scope_unverified':'The selected security document or current version remains unverified.',
    'selected_security_eps_conflict':'Common-share EPS in the specific document conflicts with the annual filing fact.',
    'selected_security_source_unavailable':'The exact SEC document needed for selected-security evidence was unavailable.',
    'vendor_history_source_unavailable':'The SEC history index needed for provider identity review was unavailable.',
    'ordinary_share_basis_unverified':'A clear common-share basis is missing. Use a method suited to this security type.',
    'operating_issuer_required':'The issuer has not qualified as an operating company.',
    'investment_company_requires_separate_method':'Investment companies require a separate method and cannot use this P/E group.',
    'industry_or_operating_scope_unverified':'Industry or operating-company scope remains unverified.',
    'at_least_three_compatible_industry_references_required':'At least 3 compatible industry references must qualify before showing a difference.',
    'vendor_context_source_unavailable':'Provider quote and filing-identity context was unavailable.',
    'industry_candidate_source_unavailable':'The provider industry candidate list was unavailable.',
    'industry_metadata_missing':'The selected company industry classification is missing.',
    'listing_classification_unavailable':'Independent listing and security-type sources were unavailable.',
    'issuer_source_unavailable':'The company filing or price source was unavailable.',
    'peer_not_collected':'Reference evidence was not collected. Resolve the selected company source gap first.',
    'source_paused_after_repeated_failures':'Repeated source failures paused further requests. Pending items remain open.',
    'cached_observation_changed':'Cached content does not match its source digest. Refresh explicitly.',
    'normalized_sec_observation_changed':'The financial facts do not match the saved source digest.',
    'normalized_observation_changed':'Provider fields do not match the saved source digest.',
    'peer_source_unavailable':'The online source did not complete, so the earlier comparison was withdrawn.',
    'commercial_identity_rights_unreviewed':'Source rights for the current commercial mode remain unreviewed.',
    'invalid_commercial_mode_configuration':'The operating-mode configuration could not be verified. Source restrictions remain.',
    'comparative_eps_missing':'The same filing lacks adjacent prior-year EPS.',
    'comparative_eps_base_nonpositive':'Prior-year EPS is zero or negative, so percentage growth is unsuitable.',
    'comparative_eps_metadata_mismatch':'Prior-year EPS does not match the selected filing form or publication date.',
    'comparative_eps_period_invalid':'The actual prior-year EPS period is not a supported full year.',
    'comparative_eps_conflict':'Prior-year EPS or its period conflicts within the same filing.',
    'comparative_eps_unit_conflict':'Prior-year EPS has conflicting currency or unit evidence.',
    'comparative_eps_value_invalid':'Prior-year EPS failed value verification.',
    'comparative_eps_growth_outside_range':'EPS change exceeds the range supported by this method.',
    'comparative_eps_input_invalid':'Verifiable same-filing annual EPS context was unavailable.',
    'amendment_source_unavailable':'The exact SEC document needed to review amendment scope was unavailable.',
    'amendment_scope_unverified':'Amendment scope or exact document remains unverified, so the EPS gap stays open.',
    'amendment_original_eps_conflict':'Original-document EPS conflicts with Companyfacts and is withheld.',
}

STYLE='''<style>
.online-peer-valuation{box-sizing:border-box;min-width:0;margin:12px 0 20px;padding:22px;border:1px solid #d7e1dc;border-radius:14px;background:#fff;color:#22372d;overflow-wrap:anywhere}
.online-peer-valuation h3{font-size:1.4rem;line-height:1.4;margin:.35rem 0 .7rem}.online-peer-valuation h4{font-size:1.05rem;margin:1rem 0 .5rem}.online-peer-valuation p{line-height:1.6;margin:.55rem 0}
.online-peer-valuation .peer-kicker{font-size:.85rem;color:#496253}.peer-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:18px 0}.peer-stats div{padding:14px;background:#f2f6f3;border:1px solid #dce5df;border-radius:10px;min-width:0}.peer-stats dt{font-size:.85rem;color:#496253}.peer-stats dd{font-size:1.35rem;font-weight:700;margin:.4rem 0 0}
.online-peer-valuation details{border-top:1px solid #dce5df;margin-top:14px;padding-top:7px}.online-peer-valuation summary{cursor:pointer;min-height:44px;display:list-item;align-content:center;font-weight:650;line-height:1.5}.online-peer-valuation a{color:#245842;text-decoration:underline}.online-peer-valuation summary:focus-visible,.online-peer-valuation a:focus-visible{outline:2px solid #245842;outline-offset:3px}
.online-peer-valuation table{width:100%;table-layout:fixed;border-collapse:collapse;margin:12px 0}.online-peer-valuation th,.online-peer-valuation td{padding:9px 6px;text-align:left;vertical-align:top;border-bottom:1px solid #dce5df;font-size:.88rem;overflow-wrap:anywhere}.online-peer-valuation code{white-space:normal;word-break:break-all;font-size:.78rem}.online-peer-valuation ul{padding-left:20px}.online-peer-valuation li{margin:.5rem 0}
@media(max-width:640px){.online-peer-valuation{padding:15px}.peer-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.online-peer-valuation table,.online-peer-valuation tbody{display:block}.online-peer-valuation thead{display:none}.online-peer-valuation tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:1px solid #dce5df;border-radius:9px;margin:12px 0;padding:7px}.online-peer-valuation td{display:block;border:0;min-width:0}.online-peer-valuation td::before{content:attr(data-label);display:block;font-size:.78rem;color:#496253;margin-bottom:4px}.online-peer-valuation td:first-child,.online-peer-valuation td:last-child{grid-column:1/-1}}
</style>'''


def _text(value):
    return escape(str(value if value is not None else 'Unavailable'))


def _number(value):
    try:return type(value) in {int,float} and abs(value)<=1e20 and math.isfinite(value)
    except (ValueError,OverflowError):return False


def _multiple(value):
    return (f'{value:,.1f}' if value>=.1 else f'{value:.3g}')+'×' if _number(value) and value>0 else 'Unavailable'


def _link(url,label):
    try:
        p=urlsplit(url) if isinstance(url,str) and len(url)<=2048 else None
        if p and p.scheme=='https' and p.hostname in {'www.sec.gov','data.sec.gov','query1.finance.yahoo.com','finance.yahoo.com','cdn.yahoofinance.com','www.nasdaqtrader.com'} and p.username is None and p.password is None and p.port is None:
            return '<a href="'+escape(url,quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(label)+'</a>'
    except ValueError:pass
    return escape(label)+' (link unverified)'


def _reason(value):
    return REASONS.get(value if isinstance(value,str) else None,'Source, identity, or field evidence could not be verified. This input is withheld.')


def _source_table(rows):
    body=''
    for row in rows:
        eps=f'{row["eps"]:,.6g}' if _number(row.get('eps')) else 'Unavailable'
        price=f'{row["price"]:,.6g}' if _number(row.get('price')) else 'Unavailable'
        cells=[('Company',_text(row.get('ticker'))),('Annual P/E',_multiple(row.get('multiple'))),
               ('Annual diluted EPS',_text(eps)+' USD/shares'),
               ('Actual fiscal period',_text(row.get('period_start'))+' → '+_text(row.get('period_end'))),
               ('Price and date',_text(price)+' USD · '+_text(row.get('price_date'))),
               ('Sources',_link(row.get('source_ref'),'SEC EPS fact')+' · '+_link(row.get('filing_ref'),'Filing')+' · '+_link(row.get('price_source_ref'),'Price source'))]
        body+='<tr>'+''.join('<td data-label="'+escape(k,quote=True)+'">'+v+'</td>' for k,v in cells)+'</tr>'
    return '<table aria-label="Annual P/E and actual fiscal periods"><thead><tr>'+''.join('<th scope="col">'+k+'</th>' for k in ('Company','Annual P/E','Annual diluted EPS','Actual fiscal period','Price and date','Sources'))+'</tr></thead><tbody>'+body+'</tbody></table>'


def _earnings_phrase(row):
    context=row.get('earnings_context') if isinstance(row.get('earnings_context'),Mapping) else {}
    growth=context.get('growth_fraction')
    if (context.get('status')=='supported' and _number(growth) and abs(growth)<=1e6
            and context.get('accession')==row.get('accession')):
        return 'Annual EPS YoY '+f'{growth*100:+.1f}%'
    return 'EPS YoY withheld. '+_reason(context.get('reason','comparative_eps_input_invalid'))


def _earnings_table(rows):
    body=''
    for row in rows:
        context=row.get('earnings_context') if isinstance(row.get('earnings_context'),Mapping) else {}
        def period(label):
            value=context.get(label+'_eps')
            if not _number(value):return 'Unavailable'
            return _text(f'{value:,.6g}')+' USD/shares<br>'+_text(context.get(label+'_period_start'))+' → '+_text(context.get(label+'_period_end'))
        cells=[('Company',_text(row.get('ticker'))),('Annual EPS change',_text(_earnings_phrase(row))),
               ('Prior-year reported EPS',period('prior')),('Current-year reported EPS',period('current')),
               ('Same-filing sources',_link(row.get('source_ref'),'SEC EPS fact')+' · '+_link(row.get('filing_ref'),'Filing'))]
        body+='<tr>'+''.join('<td data-label="'+escape(k,quote=True)+'">'+v+'</td>' for k,v in cells)+'</tr>'
    return '<h4>Earnings change context</h4><p>Diluted EPS reported in the same annual filing. Historical change does not predict future growth, and peer multiples are not adjusted for growth.</p><table aria-label="EPS change in the same annual filing"><thead><tr>'+''.join('<th scope="col">'+k+'</th>' for k in ('Company','Annual EPS change','Prior-year reported EPS','Current-year reported EPS','Same-filing sources'))+'</tr></thead><tbody>'+body+'</tbody></table>'


def _diagnostic_html(d):
    if not isinstance(d,Mapping):return '<p>No independently verifiable observation is available.</p>'
    html='<p>These independent source observations are excluded from P/E and the reference median. '+_link(d.get('candidate_source_ref'),'Candidate-list source')+'</p>'
    if d.get('sec_cik'):
        html+='<p>SEC listing association CIK '+_text(d['sec_cik'])+' · '+_link(d.get('profile_source_ref'),'Filing metadata query')+' · '+_link(d.get('facts_query_ref'),'EPS fact query')+'. A query URL does not establish that the fact was retrieved.</p>'
    for filing in d.get('annual_versions',[]):
        html+='<p>'+_text(filing.get('form'))+' · '+_text(filing.get('accession'))+' · period end '+_text(filing.get('period_end'))+' · filed '+_text(filing.get('filed'))+' · '+_link(filing.get('source_ref'),'Exact filing')+'</p>'
    html+=_selected_security_html(d.get('selected_security_scope'))
    html+=_history_html(d.get('vendor_identity_observation'))
    eps=d.get('annual_eps_observation')
    if isinstance(eps,Mapping) and _number(eps.get('eps')):
        html+='<p>Reported diluted EPS: '+_text(f'{eps["eps"]:,.6g}')+' USD/shares · '+_text(eps.get('period_start'))+' → '+_text(eps.get('period_end'))+' · filed '+_text(eps.get('filed'))+' · observed '+_text(eps.get('observed_at'))+' · '+_link(eps.get('source_ref'),'SEC EPS observation')+' · '+_link(eps.get('filing_ref'),'Filing')+'</p>'
        html+=_earnings_table([{**eps,'ticker':d.get('ticker',d.get('sec_cik'))}])
        html+=_amendment_html(eps.get('amendment_scope'))
        digest=eps.get('facts_sha256')
        html+='<p>Raw SEC response SHA-256: <code>'+(_text(digest) if isinstance(digest,str) and re.fullmatch(r'[0-9a-f]{64}',digest) else 'Unavailable')+'</code></p>'
    price=d.get('price_observation')
    if isinstance(price,Mapping):
        html+='<p>Separate price observation, excluded from valuation: '+_text(price.get('provider_symbol'))+' · '+_text(price.get('price'))+' USD · '+_text(price.get('date'))+' · observed '+_text(price.get('observed_at'))+' · '+_link(price.get('source_ref'),'Price source')+'</p>'
        html+='<p>Requested price and split history '+_text(price.get('history_range'))+'. Actual coverage '+_text(price.get('first_date'))+' → '+_text(price.get('last_date'))+'. The requested range does not prove complete history.</p>'
    else:html+='<p>Price source evidence was unavailable or failed independent field checks.</p>'
    for split in d.get('splits_observed',[]):
        html+='<p>Observed split: '+_text(split.get('date'))+' · '+_text(split.get('numerator'))+':'+_text(split.get('denominator'))+'. Adjusted EPS was not inferred.</p>'
    observation=d.get('independent_observation_not_in_benchmark')
    if isinstance(observation,Mapping):html+='<p>The selected company was calculated independently and excluded from the reference median.</p>'+_source_table([observation])
    return html


def _amendment_html(scope):
    if not isinstance(scope,Mapping) or scope.get('status')!='supported':return ''
    html='<details><summary>Amendment scope and original annual EPS evidence</summary><p>Original annual EPS was cross-checked against the exact filing and Companyfacts. The known amendment corrected a percentage in management discussion and stated that other disclosures were unchanged. Reusing original EPS is a bounded technical evidence interpretation and grants no source rights or model approval.</p>'
    html+='<p>Amendment metadata identifies Form 10-K/A, while the document records AmendmentFlag=false. General filing parsing remains restricted under its existing validation rules.</p>'
    receipts=scope.get('source_receipts',[])
    for index,(key,label) in enumerate([('original','Original filing'),('amendment','Latest amendment')]):
        filing=scope.get(key,{}) if isinstance(scope.get(key),Mapping) else {};ref=receipts[index] if isinstance(receipts,list) and len(receipts)>index else {}
        html+='<p>'+label+' · '+_text(filing.get('form'))+' · '+_text(filing.get('accessionNumber'))+' · filed '+_text(filing.get('filingDate'))+' · accepted '+_text(filing.get('acceptanceDateTime'))+' · '+_link(ref.get('source_url'),'Exact document')+' · observed '+_text(ref.get('observed_at'))+'</p><p>SHA-256 <code>'+_text(ref.get('payload_sha256'))+'</code></p>'
        if ref.get('binding_normalization')=='sec-empty-tail-script-v1':
            html+='<p>Filing-body SHA-256 <code>'+_text(ref.get('body_sha256'))+'</code>. Only the declared empty external script at the end of the SEC response was excluded.</p>'
    return html+'</details>'


def _observations_html(scope,*,compact=False):
    observations=scope.get('evidence_observations',[])
    if not isinstance(observations,list) or not observations:return ''
    html='<h4>Verified security and earnings observations</h4><p>These observations are excluded from P/E, the reference median, and saved models.</p>'
    if scope.get('reason')=='depositary_security_requires_separate_method':
        html+='<p>ADS and common shares are shown separately. A convenience USD translation is not earnings converted at the trading-date exchange rate. EPS per ADS is not calculated from rounded common-share EPS.</p>'
    has_numbers=any(isinstance(o,Mapping) and o.get('kind')=='numeric' for o in observations)
    for o in observations:
        if not isinstance(o,Mapping):continue
        if compact and has_numbers and (o.get('kind')!='numeric' or o.get('security_basis')!='ADS'):continue
        html+='<p><strong>'+_text(o.get('label'))+'</strong>'
        if _number(o.get('value')):
            unit=o.get('unit','')
            display_unit=unit.replace('/shares','/ADS' if o.get('security_basis')=='ADS' else '/common share')
            html+=': '+_text(f'{o["value"]:,.6g}')+' '+_text(display_unit)
        html+='</p>'
        if compact:
            if not has_numbers:html+='<p>'+_link(o.get('source_ref'),'Verified original evidence')+'</p>'
            continue
        if o.get('kind')=='numeric':
            html+='<p>'+_text(o.get('period_start'))+' → '+_text(o.get('period_end'))+' · original unit '+_text(o.get('unit'))+' · '+_text(o.get('concept'))+' · '+_text(o.get('namespace_uri'))+'</p>'
        if o.get('entity_cik'):
            html+='<p>Filing CIK '+_text(o.get('filing_cik'))+' · fact-context entity CIK '+_text(o.get('entity_cik'))+'</p>'
        html+='<p>'+_link(o.get('source_ref'),'Original observation source')
        for key,label in [('context_source_ref','Entity and period context'),('unit_source_ref','Original unit definition')]:
            if o.get(key):html+=' · '+_link(o[key],label)
        html+='</p>'
        if o.get('source_refs'):html+='<p>Complete note chain: '+' · '.join(_link(ref,'Original note') for ref in o['source_refs'])+'</p>'
        if o.get('location'):html+='<p>Location in filing body '+_text(o['location'])+'. The whole-document link is used because no fragment anchor is available.</p>'
        html+='<p>Filed '+_text(o.get('publication_date'))+' · observed '+_text(o.get('observed_at'))+'</p>'
    return html


def _selected_security_html(scope):
    if not isinstance(scope,Mapping) or scope.get('status') not in {'supported_common','inspection_only'}:return ''
    html='<details><summary>Selected security and related issuer symbols</summary>'
    if scope['status']=='supported_common':html+='<p>The selected common share and reported annual EPS basis were checked against exact documents. Full valuation eligibility and reference comparability require separate checks. This is bounded technical evidence.</p>'
    else:html+='<p>'+_text(_reason(scope.get('reason')))+'</p>'
    if scope.get('reason')=='successor_annual_basis_unverified':html+='<p>Security and reporting continuity evidence links the prior and current issuers, but the current issuer annual EPS denominator remains missing. EPS from the old CIK is not joined to the current denominator, and provider identity conflicts remain open.</p>'
    if scope.get('reason')=='depositary_security_requires_separate_method':html+='<p>The cover-page common-share title carries a non-trading restriction and does not itself identify the NYSE-traded ADS.</p>'
    symbols=scope.get('issuer_symbols',[])
    html+='<p>Related issuer symbols: '+_text(', '.join(str(s) for s in symbols))+'. These symbols are not individually mapped to securities. Raw cover-page symbols remain separate observations below.</p>'
    if scope.get('unassigned_issuer_symbols'):html+='<p>Related issuer symbols not individually mapped: '+_text(', '.join(scope['unassigned_issuer_symbols']))+'. Only the selected security was checked. Related symbols receive no inherited price or valuation eligibility.</p>'
    labels={'annual':'Annual filing','cover':'Verified 8-K cover','successor':'Successor issuer filing','quarter':'Quarterly filing','annual_companion':'Companion exhibit in the same annual filing','cover_companion':'Companion exhibit in the same 8-K'}
    for doc in scope.get('documents',[]):
        html+='<p>'+_text(labels.get(doc.get('role'),doc.get('role')))+' · '+_text(doc.get('form'))+' · '+_text(doc.get('accessionNumber'))+' · period end '+_text(doc.get('reportDate'))+' · filed '+_text(doc.get('filingDate'))+' · accepted '+_text(doc.get('acceptanceDateTime'))+' · observed '+_text(doc.get('observed_at'))+' · '+_link(doc.get('source_ref'),'Exact document')+'</p>'
        selected=doc.get('selected_common')
        if doc.get('parent_source_ref'):
            html+='<p>'+_text(doc.get('parent_form'))+' '+_link(doc.get('parent_source_ref'),'Parent document reference')+': '+_text(doc.get('parent_href'))+'. The period, filed date, and acceptance date belong to the same parent filing. The exhibit type is listed separately.</p>'
        if isinstance(selected,Mapping):
            html+='<p>Selected security: '+_text(selected.get('ticker'))+' · '+_text(selected.get('title'))+' · '+_text(selected.get('exchange'))+'</p>'
            html+='<p>'+ ' · '.join(_link(ref,label) for ref,label in zip(selected.get('fact_refs',[]),('Cover security title','Cover trading symbol','Cover exchange')))+'</p>'
            if selected.get('context_source_ref'):html+='<p>'+_link(selected['context_source_ref'],'Security context source')+'</p>'
            if selected.get('consistent_duplicate_refs'):html+='<p>Verified matching exchange disclosures: '+' · '.join(_link(ref,'Original fact') for ref in selected['consistent_duplicate_refs'])+'</p>'
        observations=doc.get('raw_cover_observations',[])
        if observations:html+='<ul>'+''.join('<li>'+_text(r.get('raw_symbol'))+' · '+_text(r.get('title'))+'</li>' for r in observations if isinstance(r,Mapping))+'</ul>'
        html+='<p>Raw response SHA-256 <code>'+_text(doc.get('payload_sha256'))+'</code><br>Verified filing-body SHA-256 <code>'+_text(doc.get('body_sha256'))+'</code></p>'
    for ref in scope.get('basis_refs',[]):html+='<p>'+_link(ref.get('source_ref'),'Common-share capital and earnings definition')+' · '+_text(ref.get('concept'))+'</p>'
    html+=_observations_html(scope)
    eps=scope.get('original_eps')
    if isinstance(eps,Mapping):
        html+='<p>Fact period and unit: '+_text(eps.get('period_start'))+' → '+_text(eps.get('period_end'))+' · USD/shares. Direct annual diluted EPS was separately checked against Companyfacts from the same filing.</p>'
        for proof in eps.get('proofs',[]):
            if not isinstance(proof,Mapping):continue
            html+='<p>'+_link(proof.get('source_ref'),'Original EPS fact')
            if proof.get('context_source_ref'):html+=' · '+_link(proof['context_source_ref'],'EPS period and entity context')
            if proof.get('unit_source_ref'):html+=' · '+_link(proof['unit_source_ref'],'EPS unit definition')
            html+='</p>'
    if any(d.get('binding_normalization')=='sec-empty-tail-script-v1' for d in scope.get('documents',[])):
        html+='<p>Filing-body verification excluded only the declared empty external script at the end of the SEC response. Each raw response digest remains intact, and filing-body changes remain gated.</p>'
    return html+'<p>Personal research only. This evidence grants no legal security classification, commercial source rights, or canonical data eligibility.</p></details>'


def _history_html(identity):
    if not isinstance(identity,Mapping) or not identity.get('history_source_ref'):return ''
    return '<p>The historical SEC index is used only for provider identity review. Annual EPS still comes from the selected current annual filing. '+_link(identity.get('history_source_ref'),'Official history index')+' · observed '+_text(identity.get('history_observed_at'))+' · SHA-256 <code>'+_text(identity.get('history_sha256'))+'</code></p>'


def _listing_html(v,*,compact=False):
    context=v.get('listing_context')
    if not isinstance(context,Mapping):return ''
    selection=context.get('selection')
    if selection=='recent_session':
        answer='The listing source is unavailable now. A complete listing observation from this session within 24 hours is reused with its original dates. Financials and prices are checked separately.'
    elif selection=='returned_receipt':
        answer='Listing evidence uses the complete source receipt returned in this attempt. Original source dates are shown below without renewal.'
    else:answer='No recent complete listing observation is available. Financial and price checks did not continue. Try again later.'
    html='<div class="peer-listing-context"><p><strong>'+answer+'</strong></p>'
    if context.get('observed_from'):
        html+='<p>Listing observation: '+_text(context['observed_from'])+' → '+_text(context.get('observed_to'))+'.</p>'
    if not compact:
        html+='<details><summary>Listing source dates, digests, and fetch attempts</summary>'
        html+='<p>Listing fetch attempt: '+_text(context.get('attempted_at'))+' → '+_text(context.get('completed_at'))+'.</p>'
        for ref in context.get('source_receipts',[])[:4]:
            html+='<p>'+_link(ref.get('source_url'),'Listing or SEC association source')+' · originally observed '+_text(ref.get('observed_at'))
            if ref.get('source_created_at'):html+=' · directory created '+_text(ref['source_created_at'])+' (New York time)'
            html+=' · SHA-256 <code>'+_text(ref.get('payload_sha256'))+'</code></p>'
        failures={'directory_incomplete':'Directory content is incomplete','source_access_limited':'Source access was limited; no automatic retry',
                  'source_transport_unavailable':'Source transport is unavailable','source_response_unverified':'Response URL or content was unverified',
                  'directory_schema_invalid':'Directory schema failed verification','directory_date_invalid':'Directory creation date is stale or in the future'}
        for attempt in context.get('source_attempts',[])[:4]:
            message=failures.get(attempt.get('reason'),'A response was received, but complete listing evidence was not verified')
            html+='<p>Fetch attempt '+_text(attempt.get('observed_at',context.get('attempted_at')))+' · '+_link(attempt.get('source_url'),'Queried source')+' · '+message
            if type(attempt.get('byte_count')) is int:html+=' · '+str(attempt['byte_count'])+' bytes'
            if attempt.get('payload_sha256'):html+=' · SHA-256 <code>'+_text(attempt['payload_sha256'])+'</code>'
            html+='</p>'
        html+='</details>'
    return html+'</div>'


def _excluded_html(v):
    excluded = v.get('excluded')
    rows = [row for row in excluded if isinstance(row, Mapping)] if isinstance(excluded, list) else []
    if not rows:
        return ''
    items = ''.join(
        '<li><details><summary>'+_text(row.get('ticker'))+': '+_text(_reason(row.get('reason')))
        +'</summary>'+_diagnostic_html(row.get('diagnostics'))+'</details></li>'
        for row in rows
    )
    return '<details><summary>Excluded reference companies and reasons ('+str(len(rows))+')</summary><ul>'+items+'</ul></details>'


def _disclosure(v,rows,*,include_excluded=True):
    html=_listing_html(v)+'<p>The automatically screened industry reference group requires the same provider industry, SEC industry code, common-share type, independent issuer, and price date. Actual fiscal start and end dates may each differ by up to '+str(FISCAL_WINDOW_DAYS)+' days. These are not identical periods or analyst-approved economic peers.</p>'
    html+='<p>The candidate list contains '+_text(v.get('industry_candidate_total'))+' records. This attempt checks at most 12 other companies in provider-list order and does not establish complete industry coverage.</p>'
    if v.get('industry_source_ref'):
        html+='<p>'+_link(v['industry_source_ref'],'Candidate-list source')+' · observed '+_text(v.get('industry_observed_at'))+'</p>'
    context=v.get('subject_source_context')
    if isinstance(context,Mapping) and context:
        html+='<h4>Selected-company filing metadata and EPS leads</h4><p>CIK '+_text(context.get('sec_cik'))+' · '+_link(context.get('profile_source_ref'),'SEC filing metadata')+' · '+_link(context.get('facts_query_ref'),'EPS fact query')+' · observed '+_text(context.get('profile_observed_at'))+'. Metadata alone does not verify the corresponding EPS fact.</p><ul>'
        for filing in context.get('annual_versions',[]):
            html+='<li>'+_text(filing.get('form'))+' · '+_text(filing.get('accession'))+' · period end '+_text(filing.get('period_end'))+' · filed '+_text(filing.get('filed'))+' · accepted '+_text(filing.get('accepted_at'))+' · '+_link(filing.get('source_ref'),'Exact filing')+'</li>'
        html+='</ul>'
        html+=_selected_security_html(context.get('selected_security_scope'))
        if not rows:html+=_history_html(context.get('vendor_identity_observation'))
    if rows:html+=_source_table(rows)+_earnings_table(rows)
    if include_excluded:html+=_excluded_html(v)
    html+='<details><summary>Field definitions, observation dates, and source digests</summary>'
    for row in rows:
        html+='<h4>'+_text(row.get('ticker'))+'</h4><p>us-gaap:EarningsPerShareDiluted · USD/shares · '+_text(row.get('form'))+' · accession '+_text(row.get('accession'))+' · filed '+_text(row.get('filed'))+'</p>'
        html+=_amendment_html(row.get('amendment_scope'))
        if row.get('ticker')!=v.get('ticker'):html+=_selected_security_html(row.get('selected_security_scope'))
        html+='<p>Financial facts observed '+_text(row.get('observed_at'))+' · price observed '+_text(row.get('price_observed_at'))+' · provider identity observed '+_text(row.get('vendor_observed_at'))+'.</p>'
        html+='<p>Requested price and split history '+_text(row.get('price_history_range'))+'. Actual coverage '+_text(row.get('price_history_first_date'))+' → '+_text(row.get('price_history_last_date'))+'. The requested range does not prove complete history.</p>'
        identity=row.get('vendor_filing') if isinstance(row.get('vendor_filing'),Mapping) else {}
        html+='<p>CIK '+_text(row.get('sec_cik'))+' · '+_link(identity.get('source_ref'),'Provider filing-identity evidence')+'. A current match does not prove historical security continuity or issuer domicile.</p>'
        html+=_history_html(identity)
        for key,label in [('facts_sha256','Raw SEC response SHA-256'),('price_sha256','Raw price response SHA-256'),('vendor_normalized_sha256','Normalized provider SHA-256')]:
            value=row.get(key)
            html+='<p>'+label+': <code>'+(_text(value) if isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) else 'Unavailable')+'</code></p>'
    html+='</details><p>Source rights allow personal research inspection only. Commercial use and redistribution of price and provider data remain unreviewed. This field grants no new SEC commercial-data approval and does not update saved models, records, or coverage status.</p>'
    return html


def online_peer_valuation_html(view,*,sources_only=False):
    v=view if isinstance(view,Mapping) else {}
    if v.get('status')=='not_requested':return ''
    subject=v.get('subject') if isinstance(v.get('subject'),Mapping) else None
    peers=[r for r in v.get('peers',[]) if isinstance(r,Mapping)] if isinstance(v.get('peers'),list) else []
    rows=([subject] if subject else [])+peers
    if sources_only:
        return STYLE+'<section class="online-peer-valuation" aria-label="Online peer valuation sources"><h3>Online peer valuation sources</h3><p>'+_text(_reason(v.get('reason')))+'</p><p>Reported annual diluted P/E uses a same-day close divided by reported annual diluted EPS. This is not TTM or forecast P/E.</p>'+_disclosure(v,rows)+'</section>'
    supported=(v.get('status')=='research_comparison' and subject is not None and subject.get('ticker')==v.get('ticker')
               and len(peers)>=MIN_PEERS and v.get('peer_count')==len(peers)
               and _number(v.get('premium_fraction')) and _number(v.get('peer_median')) and v['peer_median']>0)
    headline='Relative valuation withheld'
    if supported:
        premium=v['premium_fraction'];amount=f'{abs(premium)*100:.1f}%' if abs(premium)>=.0005 else '<0.1%'
        headline=('Annual P/E equals the industry reference median' if premium==0 else 'Annual P/E is '+amount+(' above' if premium>0 else ' below')+' the industry reference median')
    kicker='Online sources · reported annual diluted P/E · not TTM or forecast'
    html=STYLE+'<section class="online-peer-valuation" aria-label="Online peer valuation"><p class="peer-kicker">'+kicker+'</p><h3>'+_text(headline)+'</h3>'
    if v.get('attempted_at'):html+='<p>Source query attempted '+_text(v['attempted_at'])+'</p>'
    html+=_listing_html(v,compact=True)
    if not supported:html+='<p>'+_text(_reason(v.get('reason')))+'</p>'
    html+='<p>This single-metric comparison is not an undervalued or overvalued conclusion. It does not adjust for business mix, growth, margins, capital needs, or risk.</p>'
    stats=[('Selected annual P/E',_multiple(subject.get('multiple')) if subject else 'Unavailable'),
           ('Industry reference median',_multiple(v.get('peer_median')) if supported else 'Withheld'),
           ('Qualified references',str(len(peers))+' companies' if subject else 'Not assessed'),('Price date',_text(subject.get('price_date')) if subject else 'Unavailable')]
    html+='<dl class="peer-stats">'+''.join('<div><dt>'+label+'</dt><dd>'+value+'</dd></div>' for label,value in stats)+'</dl>'
    if subject:
        html += '<p><strong>How P/E is calculated</strong> Same-day close ÷ reported annual diluted EPS.</p>'
        if supported:
            html += ('<p><strong>How the difference is calculated</strong> Selected company '+_multiple(subject.get('multiple'))
                     +' ÷ reference median '+_multiple(v['peer_median'])+' − 1. The percentage uses unrounded multiples.</p>')
        if peers:
            members = ', '.join(_text(peer.get('ticker')) for peer in peers)
            html += ('<p><strong>Why these references qualify</strong> '+members
                     +'. Provider industry and SEC industry code match. Each is a common share of an independent issuer with a same-day close, '
                     +'and actual fiscal start and end dates each differ by no more than '+str(FISCAL_WINDOW_DAYS)+' days.</p>')
        html += _excluded_html(v)
    scope=v.get('subject_source_context',{}).get('selected_security_scope',{}) if isinstance(v.get('subject_source_context'),Mapping) else {}
    if not subject and isinstance(scope,Mapping) and scope.get('status')=='inspection_only':html+=_observations_html(scope,compact=True)
    if subject:
        html+='<h4>Earnings change context</h4><p><strong>'+_text(_earnings_phrase(subject))+'</strong> · reported in the same annual filing.</p><p>Historical change does not predict future growth. Reference multiples are not adjusted for growth. Expand the evidence below to check current and prior EPS and actual periods for each company.</p>'
        if subject.get('amendment_scope'):html+='<p>EPS uses the cross-checked original annual filing. Amendment scope, sources, and flag differences are shown in the evidence below.</p>'
    if not supported:
        html+=('<p>At least 3 compatible industry references must qualify before a premium or discount is shown. Currently '+str(len(peers))+' qualify.</p>' if subject
               else '<p>Selected-company valuation evidence remains unverified, so references have not been assessed. At least 3 compatible industry references must qualify before a premium or discount is shown.</p>')
    html+='<details><summary>View actual fiscal periods, prices, and sources</summary>'+_disclosure(v,rows,include_excluded=not subject)+'</details>'
    html+='<details><summary>Why other valuation methods are withheld</summary><p>TTM or forecast P/E, P/S, P/FCF, and EV/EBITDA each require separate checks of period, share count, enterprise value, and component definitions. No method is inferred from a listing or another multiple.</p></details><p><a href="?mode=research&amp;page=discover#peer-coverage-sample" target="_self">View cross-industry peer coverage</a></p></section>'
    return html
