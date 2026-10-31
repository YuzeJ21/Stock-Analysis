"""Source-observed research paths, independent of analysis eligibility."""
from html import escape
from src.online_company_identity import _mode_reason
from src.security_classification import validated_company_context

BANK_SICS=frozenset({'6021','6022','6029','6035','6036'})
WRAPPERS=frozenset({'etf','preferred','debt','unit','warrant','right'})
PATHS={
 'investment_company':('Investment-company research','Review holdings, net asset value, fees and distributions. Ordinary operating-company peer multiples may not fit this reporting structure.'),
 'bank':('Bank research','Keep net interest income, noninterest income and credit costs distinct. Book value, earnings quality and capital need their own source evidence; a generic operating-company multiple is insufficient.'),
 'blank_check':('Blank-check company research','Review transaction status, cash and redemption terms before treating this as an operating business.'),
 'operating_company_candidate':('Operating-company research candidate','Annual reporting and an operating-entity observation are available. Financial fields, comparable peers, price identity and valuation remain separate checks.'),
 'issuer_review':('Issuer research path unresolved','The observed reporting profile does not yet establish an operating-company research path.'),
 'security_wrapper':('Instrument-specific research','This directory description identifies a fund or other security wrapper. Inspect its terms and underlying exposure before applying operating-company valuation.'),
 'unresolved':('Research path not yet established','Check listing and issuer type to inspect source evidence. No analysis qualification is inferred.'),
}


def research_scope(context,ticker):
 result=dict(ticker=ticker,sec_cik=None,path='unresolved',issuer_path='unresolved',security_types=[],
  analysis_eligibility_established=False,legal_security_type_established=False,
  domicile_established=False,active_status_established=False,point_in_time_established=False)
 if _mode_reason('research'):return result
 p=validated_company_context(context,ticker)
 if p is None:return result
 types=sorted({r['security_type'] for r in p['listing_rows']})
 profile=p['issuer_profile'];issuer='issuer_review'
 if profile.get('status')=='inspection_only':
  reporting=profile['reporting_profile'];sic=profile['sic']
  if (reporting=='investment_company_reporting' or profile.get('entity_type')=='investment-company'
      or any(form in profile.get('form_counts',{}) for form in ('N-CSR','N-CSRS','N-CEN','NPORT-P','N-PORT'))):issuer='investment_company'
  elif sic=='6770':issuer='blank_check'
  elif sic in BANK_SICS:issuer='bank'
  elif profile.get('entity_type')=='operating' and reporting in {'domestic_annual_reporting','foreign_annual_reporting'}:issuer='operating_company_candidate'
 result.update(sec_cik=p['sec_cik'],issuer_path=issuer,security_types=types,path='security_wrapper' if WRAPPERS.intersection(types) else issuer)
 return result


def research_scope_html(result):
 title,detail=PATHS.get(result.get('path'),PATHS['unresolved'])
 return ('<aside class="research-path" aria-label="Research path"><h4>'+escape(title)+'</h4><p>'+escape(detail)+
  '</p><p><small>Source-observed research path only; legal security type and analysis eligibility remain unverified.</small></p></aside>')
