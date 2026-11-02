"""Exact-source selected-security scopes, distinct from general classification."""
from collections.abc import Mapping
from datetime import datetime,timedelta,timezone
import base64,binascii,hashlib,re
import xml.etree.ElementTree as ET

from src.sec_selected_security_policies import POLICIES
from src.online_company_identity import _mode_reason
from src.company_sec_online_preview import _iso_date,_utc_timestamp
from src.sec_exact_filing import MAX_FILING_BYTES,_fetch_html,_digest,RIGHTS
from src.sec_inline_filing import X,IX,_tree,_qname,_taxonomy,_date_fact
from src.annual_amendment_evidence import _original_eps
from src.security_classification import classify_description

SCHEMA='sec-selected-security-v1'
KEYS=('form','reportDate','filingDate','acceptanceDateTime','accessionNumber','primaryDocument','isInlineXBRL','isXBRL')
ANNUAL={'10-K','10-K/A','20-F','20-F/A'}
IDENTITY_FORMS={'8-K','8-K/A','8-K12B','8-K12B/A'}
FINANCIAL_FORMS=ANNUAL|{'10-Q','10-Q/A'}
FUND_FORMS={'N-CSR','N-CSRS','N-CEN','NPORT-P','N-PORT'}


def _fresh(stamp,now):
    observed=_utc_timestamp(stamp)
    return observed is not None and timedelta(0)<=now-observed<=timedelta(hours=24)


def _require(value):
    if not value:raise ValueError('selected_security_scope_unverified')


def known_security_scope(ticker,cik):
    return any(p['ticker']==ticker and p['sec_cik']==cik for p in POLICIES)


def _metadata(profile):
    recent=profile['payload']['filings']['recent']
    _require(all(isinstance(recent.get(k),list) for k in KEYS))
    n=len(recent['form']);_require(0<n<=2000 and all(len(recent[k])==n for k in KEYS))
    return [dict(zip(KEYS,r)) for r in zip(*(recent[k] for k in KEYS))]


def _policy(ticker,cik,profile,now):
    _require(isinstance(now,datetime) and now.utcoffset() is not None and isinstance(profile,Mapping))
    _require(profile.get('status')=='ready' and profile.get('source_url')==f'https://data.sec.gov/submissions/CIK{cik}.json' and _fresh(profile.get('observed_at'),now))
    body=profile['payload'];_require(str(int(body['cik'])).zfill(10)==cik)
    _require('normalized_sha256' not in profile or profile['normalized_sha256']==_digest(body))
    policies=[p for p in POLICIES if (p['ticker'],p['sec_cik'])==(ticker,cik)]
    if len(policies)!=1:return None
    p=policies[0];rows=_metadata(profile)
    _require(isinstance(body.get('tickers'),list) and len(set(body['tickers']))==len(body['tickers']) and sorted(body['tickers'])==p['issuer_symbols'])
    _require(isinstance(body.get('exchanges'),list) and len(body['exchanges'])==len(body['tickers']))
    for role,doc in p['documents'].items():
        forms=ANNUAL if role=='annual' else {'8-K','8-K/A'} if role=='cover' else {'8-K12B','8-K12B/A'} if role=='successor' else {'10-Q','10-Q/A'}
        chosen=[r for r in rows if r['form'] in forms];_require(chosen)
        _require(all(_iso_date(r['reportDate']) and _iso_date(r['filingDate']) and _utc_timestamp(r['acceptanceDateTime']) for r in chosen))
        if role in {'annual','quarter'}:
            end=max(r['reportDate'] for r in chosen);chosen=[r for r in chosen if r['reportDate']==end]
        filed=max(r['filingDate'] for r in chosen);chosen=[r for r in chosen if r['filingDate']==filed]
        accepted=max(_utc_timestamp(r['acceptanceDateTime']) for r in chosen)
        chosen=[r for r in chosen if _utc_timestamp(r['acceptanceDateTime'])==accepted];_require(len(chosen)==1)
        selected=chosen[0];expected=doc['metadata']
        _require(all((_utc_timestamp(selected[k])==_utc_timestamp(expected[k]) if k=='acceptanceDateTime' else type(selected[k]) is type(expected[k]) and selected[k]==expected[k]) for k in KEYS))
        _require(_iso_date(selected['reportDate'])<=_iso_date(selected['filingDate'])<=now.date() and accepted<=now)
    return p


def _url(cik,meta):
    _require(re.fullmatch(r'\d{10}-\d{2}-\d{6}',meta['accessionNumber']) and re.fullmatch(r'[A-Za-z0-9_.-]{1,200}',meta['primaryDocument']) and '..' not in meta['primaryDocument'])
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{meta["accessionNumber"].replace("-","")}/{meta["primaryDocument"]}'


def fetch_selected_security_evidence(ticker,cik,profile,*,user_agent,fetcher=None,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode);held=dict(status='unavailable',reason=reason or 'selected_security_source_unavailable')
    if reason:return held
    try:p=_policy(ticker,cik,profile,observed_at or datetime.now(timezone.utc))
    except (ValueError,KeyError,TypeError,AttributeError,OverflowError):p=None
    if p is None:return dict(status='not_applicable',reason='selected_security_scope_unverified')
    try:
        _require(isinstance(user_agent,str) and user_agent.strip() and not any(c in user_agent for c in '\r\n'))
        documents={}
        for role,doc in p['documents'].items():
            url=_url(cik,doc['metadata']);raw,headers,final=(fetcher or _fetch_html)(url,user_agent.strip())
            _require(isinstance(raw,bytes) and 0<len(raw)<=MAX_FILING_BYTES and final==url)
            stamp=(observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            documents[role]=dict(status='ready',source_url=url,observed_at=stamp,payload_sha256=hashlib.sha256(raw).hexdigest(),payload_raw_base64=base64.b64encode(raw).decode())
        return dict(schema_version=SCHEMA,status='observed',ticker=ticker,sec_cik=cik,documents=documents)
    except (ValueError,KeyError,TypeError,AttributeError,OSError,RuntimeError,OverflowError):return held


def _contexts(root,cik):
    result={}
    for node in root.iter(f'{{{X}}}context'):
        entity=node.find(f'{{{X}}}entity');period=node.find(f'{{{X}}}period')
        if entity is None or period is None:continue
        identifiers=entity.findall(f'{{{X}}}identifier')
        if len(identifiers)!=1 or identifiers[0].get('scheme')!='http://www.sec.gov/CIK' or identifiers[0].text!=cik:continue
        result[node.get('id')]=node
    return result


def _cover_date(node,ns):
    uri,name=_qname(node.get('format'),ns)
    if (uri,name)!=('http://www.xbrl.org/inlineXBRL/transformation/2015-02-26','datemonthdayyearen'):return _date_fact(node,ns)
    text=' '.join(''.join(node.itertext()).split());match=re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (\d{4})',text)
    months={m:i+1 for i,m in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'))}
    return _iso_date(f'{match[3]}-{months[match[1]]:02d}-{int(match[2]):02d}') if match and match[1] in months else None


def _cover(raw,cik,meta,doc,url):
    root,ns=_tree(raw);contexts=_contexts(root,cik);facts={};groups={};forms=set();ends=set()
    for node in root.iter(f'{{{IX}}}nonNumeric'):
        uri,name=_qname(node.get('name'),ns)
        if not uri or not re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}',uri) or node.get('contextRef') not in contexts:continue
        context=contexts[node.get('contextRef')];period=context.find(f'{{{X}}}period')
        end=period.find(f'{{{X}}}endDate')
        if end is None or end.text!=meta['reportDate']:continue
        text=' '.join(''.join(node.itertext()).split());facts[node.get('id')]=node
        if name=='DocumentType':forms.add(text)
        if name=='DocumentPeriodEndDate':ends.add(_cover_date(node,ns))
        if name in {'TradingSymbol','Security12bTitle','SecurityExchangeName'}:
            _require(node.get('continuedAt') is None and node.get('target') in {None,''} and node.get('tupleRef') is None and node.get('{http://www.w3.org/2001/XMLSchema-instance}nil') in {None,'false','0'})
            values=groups.setdefault(node.get('contextRef'),{});_require(name not in values);values[name]=(text,node.get('id'))
    _require(forms=={meta['form']} and ends=={_iso_date(meta['reportDate'])})
    selected=[];observations=[];common_symbols=set()
    for context_id,values in groups.items():
        if set(values)!={'TradingSymbol','Security12bTitle','SecurityExchangeName'}:continue
        title,symbol,exchange=(values[k][0] for k in ('Security12bTitle','TradingSymbol','SecurityExchangeName'))
        observations.append(dict(raw_symbol=symbol,title=title,exchange=exchange,context_id=context_id))
        if classify_description(title,False)['security_type']=='common_shares':common_symbols.add(symbol)
        if [values[k][1] for k in ('Security12bTitle','TradingSymbol','SecurityExchangeName')]==doc['cover_fact_ids']:
            members=list(contexts[context_id].iter('{http://xbrl.org/2006/xbrldi}explicitMember'))
            _require(len(list(contexts[context_id].iter('{http://xbrl.org/2006/xbrldi}typedMember')))==0 and contexts[context_id].find(f'{{{X}}}scenario') is None)
            _require(len(members)==1 and _qname(members[0].get('dimension'),ns)[1]=='StatementClassOfStockAxis' and _taxonomy(_qname(members[0].get('dimension'),ns)[0])=='us-gaap')
            _require(_qname(members[0].text,ns)[1]=='CommonStockMember' and _taxonomy(_qname(members[0].text,ns)[0])=='us-gaap')
            venue={'The New York Stock Exchange':'NYSE','New York Stock Exchange':'NYSE','New York Stock Exchange LLC':'NYSE','NYSE':'NYSE','Nasdaq':'Nasdaq','NASDAQ':'Nasdaq'}.get(exchange)
            _require(venue is not None)
            selected.append(dict(ticker=symbol,title=title,exchange=exchange,venue=venue,context_id=context_id,fact_refs=[url+'#'+i for i in doc['cover_fact_ids']]))
    _require(len(selected)==1 and common_symbols=={selected[0]['ticker']})
    return root,ns,contexts,selected[0],observations


def validate_selected_security_evidence(packet,*,ticker,cik,profile,issuer_symbols,as_of):
    held=dict(status='withheld',reason='selected_security_scope_unverified')
    if _mode_reason('research'):return held
    try:
        _require(isinstance(packet,Mapping) and packet.get('schema_version')==SCHEMA and packet.get('status')=='observed' and (packet.get('ticker'),packet.get('sec_cik'))==(ticker,cik))
        p=_policy(ticker,cik,profile,as_of);_require(p is not None and sorted(issuer_symbols)==p['issuer_symbols'])
        documents=[];eps=None;basis=[]
        for role,doc in p['documents'].items():
            ref=packet['documents'][role];encoded=ref['payload_raw_base64'];url=_url(cik,doc['metadata'])
            _require(ref.get('status')=='ready' and ref.get('source_url')==url and _fresh(ref.get('observed_at'),as_of))
            _require(isinstance(encoded,str) and 0<len(encoded)<=4*((MAX_FILING_BYTES+2)//3))
            raw=base64.b64decode(encoded,validate=True)
            _require(0<len(raw)<=MAX_FILING_BYTES and hashlib.sha256(raw).hexdigest()==doc['sha256']==ref.get('payload_sha256'))
            item=dict(role=role,**doc['metadata'],source_ref=url,observed_at=ref['observed_at'],payload_sha256=doc['sha256'])
            if p['kind']=='supported_common':
                root,ns,contexts,common,other=_cover(raw,cik,doc['metadata'],doc,url);_require(common['ticker']==ticker)
                item.update(selected_common=common,raw_cover_observations=other)
                if role=='annual':
                    eps=_original_eps(raw,cik,doc['metadata']['reportDate'],url)
                    ids={n.get('id'):n for n in root.iter() if n.get('id')}
                    for identity in p['basis_fact_ids']:
                        n=ids[identity];uri,name=_qname(n.get('name'),ns)
                        _require(_taxonomy(uri)=='us-gaap' and name in {'CommonStockParOrStatedValuePerShare','StockholdersEquityNoteDisclosureTextBlock','EarningsPerSharePolicyTextBlock','ScheduleOfEarningsPerShareBasicAndDilutedTableTextBlock'} and n.get('contextRef') in contexts)
                        _require(bool(''.join(n.itertext()).strip()))
                        basis.append(dict(concept=name,source_ref=url+'#'+identity,context_id=n.get('contextRef')))
            documents.append(item)
        result=dict(status=p['kind'],reason=p['reason'],policy_id=p['policy_id'],ticker=ticker,sec_cik=cik,issuer_symbols=p['issuer_symbols'],documents=documents,basis_refs=basis,alias_mappings_established=False,technical_interpretation_only=True,commercial_eligible=False,rights_status=RIGHTS)
        if p['kind']=='supported_common':_require(eps is not None);result['original_eps']=eps
        return result
    except (ValueError,KeyError,TypeError,AttributeError,OverflowError,RecursionError,binascii.Error,ET.ParseError):return held
