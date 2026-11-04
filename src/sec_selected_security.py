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
from src.sec_security_document_set import companion_source,bind_document_set,MAX_SCOPE_BYTES
from src.sec_security_observations import inspect_observations

SCHEMA='sec-selected-security-v1'
KEYS=('form','reportDate','filingDate','acceptanceDateTime','accessionNumber','primaryDocument','isInlineXBRL','isXBRL')
ANNUAL={'10-K','10-K/A','20-F','20-F/A'}
IDENTITY_FORMS={'8-K','8-K/A','8-K12B','8-K12B/A'}
FINANCIAL_FORMS=ANNUAL|{'10-Q','10-Q/A'}
_FUND_BASE_FORMS={'N-CSR','N-CSRS','N-CEN','NPORT-P','N-PORT'}
FUND_FORMS=_FUND_BASE_FORMS|{form+'/A' for form in _FUND_BASE_FORMS}
_TAIL_SCRIPT=re.compile(rb'<script type="text/javascript"\s+src="/[A-Za-z0-9_-]{1,80}(?:/[A-Za-z0-9_-]{1,80}){1,15}"></script>(?=</(?:body|BODY)>\s*</(?:html|HTML)>\s*(?:</TEXT>\s*</DOCUMENT>\s*)?\Z)')


def _bound_body(raw,normalization):
    if normalization is None:return raw
    _require(normalization=='sec-empty-tail-script-v1')
    # Only this empty, relative-path, external tail script is response decoration.
    # Every other source byte remains bound; scripts are never executed here.
    return _TAIL_SCRIPT.sub(b'',raw)


def _fresh(stamp,now):
    observed=_utc_timestamp(stamp)
    return observed is not None and timedelta(0)<=now-observed<=timedelta(hours=24)


def is_investment_company_form(form):
    return isinstance(form,str) and form in FUND_FORMS


def valid_profile_metadata_shape(recent,*,max_rows):
    if not isinstance(recent,Mapping):return False
    columns=('form','reportDate','filingDate','accessionNumber','primaryDocument')
    if 'acceptanceDateTime' in recent:columns+=('acceptanceDateTime',)
    if 'isInlineXBRL' in recent or 'isXBRL' in recent:columns+=('isInlineXBRL','isXBRL')
    if not all(isinstance(recent.get(k),list) for k in columns):return False
    n=len(recent['form'])
    if not 0<n<=max_rows or any(len(recent[k])!=n for k in columns):return False
    return all(all(type(v) is int and v in {0,1} for v in recent[k]) if k in {'isInlineXBRL','isXBRL'} else all(isinstance(v,str) for v in recent[k]) for k in columns)


def _require(value):
    if not value:raise ValueError('selected_security_scope_unverified')


def known_security_scope(ticker,cik):
    return any(p['ticker']==ticker and p['sec_cik']==cik for p in POLICIES)


def _metadata(profile):
    recent=profile['payload']['filings']['recent']
    _require(all(isinstance(recent.get(k),list) for k in KEYS) and valid_profile_metadata_shape(recent,max_rows=2000))
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
    if p.get('requires_absent_annual'):_require(not any(r['form'] in ANNUAL for r in rows))
    _require(isinstance(body.get('tickers'),list) and len(set(body['tickers']))==len(body['tickers']) and sorted(body['tickers'])==p['issuer_symbols'])
    _require(isinstance(body.get('exchanges'),list) and len(body['exchanges'])==len(body['tickers']))
    for role,doc in p['documents'].items():
        forms=ANNUAL if role=='annual' else IDENTITY_FORMS if role=='cover' else {'8-K12B','8-K12B/A'} if role=='successor' else {'10-Q','10-Q/A'}
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
        documents={};total=0
        _require(0<len(p['documents'])<=2)
        def capture(url):
            nonlocal total
            raw,headers,final=(fetcher or _fetch_html)(url,user_agent.strip())
            _require(isinstance(raw,bytes) and 0<len(raw)<=MAX_FILING_BYTES and final==url)
            total+=len(raw);_require(total<=MAX_SCOPE_BYTES)
            stamp=(observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            return dict(status='ready',source_url=url,observed_at=stamp,payload_sha256=hashlib.sha256(raw).hexdigest(),payload_raw_base64=base64.b64encode(raw).decode())
        for role,doc in p['documents'].items():
            url=_url(cik,doc['metadata']);documents[role]=capture(url)
            companion=companion_source(doc,url)
            if companion is not None:documents[role]['companion']=capture(companion[1])
        return dict(schema_version=SCHEMA,status='observed',ticker=ticker,sec_cik=cik,documents=documents)
    except (ValueError,KeyError,TypeError,AttributeError,OSError,RuntimeError,OverflowError):return held


def _contexts(root,cik):
    result={}
    for node in root.iter(f'{{{X}}}context'):
        entity=node.find(f'{{{X}}}entity');period=node.find(f'{{{X}}}period')
        if entity is None or period is None:continue
        identifiers=entity.findall(f'{{{X}}}identifier')
        if len(identifiers)!=1 or len(identifiers[0])!=0 or identifiers[0].get('scheme')!='http://www.sec.gov/CIK' or identifiers[0].text!=cik:continue
        if any(len(value)!=0 for value in period if value.tag in {f'{{{X}}}startDate',f'{{{X}}}endDate',f'{{{X}}}instant'}):continue
        result[node.get('id')]=node
    return result


def _cover_date(node,ns):
    uri,name=_qname(node.get('format'),ns)
    if (uri,name) not in {('http://www.xbrl.org/inlineXBRL/transformation/2015-02-26','datemonthdayyearen'),('http://www.xbrl.org/inlineXBRL/transformation/2022-02-16','date-monthname-day-year-en')}:return _date_fact(node,ns)
    text=' '.join(''.join(node.itertext()).split());match=re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (\d{4})',text)
    months={m:i+1 for i,m in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'))}
    return _iso_date(f'{match[3]}-{months[match[1]]:02d}-{int(match[2]):02d}') if match and match[1] in months else None


def _cover(raw,cik,meta,doc,url,*,parsed=None,source_refs=None):
    root,ns=_tree(raw) if parsed is None else parsed;contexts=_contexts(root,cik);facts={};groups={};forms=set();ends=set()
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
            values=groups.setdefault(node.get('contextRef'),{});values.setdefault(name,[]).append((text,node.get('id'),uri,node))
    _require(forms=={meta['form']} and ends=={_iso_date(meta['reportDate'])})
    allowed=doc.get('cover_duplicate_groups',[]);_require(isinstance(allowed,list) and len(allowed)<=4);used=set();duplicate_refs=[]
    for context_id,values in groups.items():
        for name,entries in values.items():
            if len(entries)>1:
                matching=[(i,g) for i,g in enumerate(allowed) if isinstance(g,Mapping) and g.get('concept')==name and g.get('context_id')==context_id and all(e[2]==g.get('namespace_uri') for e in entries) and sorted(g.get('fact_ids',[]))==sorted(e[1] for e in entries)]
                _require(len(matching)==1 and name=='SecurityExchangeName' and len(entries)==2 and len({e[0] for e in entries})==1)
                _require(all(all(e[3].get(a) is None for a in ('target','continuedAt','tupleRef','format','{http://www.w3.org/2001/XMLSchema-instance}nil')) for e in entries))
                used.add(matching[0][0]);duplicate_refs.extend((source_refs[e[1]] if source_refs is not None else url+'#'+e[1]) for e in entries)
            chosen=[e for e in entries if e[1] in doc['cover_fact_ids']]
            values[name]=(chosen[0] if len(chosen)==1 else entries[0])[:2]
    _require(used==set(range(len(allowed))))
    selected=[];observations=[];common_symbols=set()
    for context_id,values in groups.items():
        if set(values)!={'TradingSymbol','Security12bTitle','SecurityExchangeName'}:continue
        title,symbol,exchange=(values[k][0] for k in ('Security12bTitle','TradingSymbol','SecurityExchangeName'))
        observations.append(dict(raw_symbol=symbol,title=title,exchange=exchange,context_id=context_id))
        if classify_description(title,False)['security_type']=='common_shares':common_symbols.add(symbol)
        if [values[k][1] for k in ('Security12bTitle','TradingSymbol','SecurityExchangeName')]==doc['cover_fact_ids']:
            members=list(contexts[context_id].iter('{http://xbrl.org/2006/xbrldi}explicitMember'))
            _require(len(list(contexts[context_id].iter('{http://xbrl.org/2006/xbrldi}typedMember')))==0 and contexts[context_id].find(f'{{{X}}}scenario') is None)
            declared=doc.get('cover_context')
            if declared is not None:
                _require(isinstance(declared,Mapping) and declared.get('kind')=='dimensionless' and context_id==declared.get('context_id'))
                context=contexts[context_id];entity=context.find(f'{{{X}}}entity');period=context.find(f'{{{X}}}period')
                _require(len(context)==2 and len(entity)==1 and len(members)==0 and len(period)==2)
                _require(period.findtext(f'{{{X}}}startDate')==declared.get('period_start') and _iso_date(declared.get('period_start')) is not None)
            else:
                _require(len(members)==1 and _qname(members[0].get('dimension'),ns)[1]=='StatementClassOfStockAxis' and _taxonomy(_qname(members[0].get('dimension'),ns)[0])=='us-gaap')
                _require(_qname(members[0].text,ns)[1]=='CommonStockMember' and _taxonomy(_qname(members[0].text,ns)[0])=='us-gaap')
            venue={'The New York Stock Exchange':'NYSE','New York Stock Exchange':'NYSE','New York Stock Exchange LLC':'NYSE','NYSE':'NYSE','Nasdaq':'Nasdaq','NASDAQ':'Nasdaq'}.get(exchange)
            _require(venue is not None)
            common=dict(ticker=symbol,title=title,exchange=exchange,venue=venue,context_id=context_id,fact_refs=[source_refs[i] if source_refs is not None else url+'#'+i for i in doc['cover_fact_ids']])
            if source_refs is not None:common['context_source_ref']=source_refs[context_id]
            if duplicate_refs:common['consistent_duplicate_refs']=duplicate_refs
            selected.append(common)
    _require(len(selected)==1 and common_symbols=={selected[0]['ticker']})
    return root,ns,contexts,selected[0],observations


def validate_selected_security_evidence(packet,*,ticker,cik,profile,issuer_symbols,as_of):
    held=dict(status='withheld',reason='selected_security_scope_unverified')
    if _mode_reason('research'):return held
    try:
        _require(isinstance(packet,Mapping) and packet.get('schema_version')==SCHEMA and packet.get('status')=='observed' and (packet.get('ticker'),packet.get('sec_cik'))==(ticker,cik))
        p=_policy(ticker,cik,profile,as_of);_require(p is not None and sorted(issuer_symbols)==p['issuer_symbols'])
        documents=[];eps=None;basis=[];observations=[];total=0
        _require(0<len(p['documents'])<=2 and set(packet['documents'])==set(p['documents']))
        for role,doc in p['documents'].items():
            ref=packet['documents'][role];encoded=ref['payload_raw_base64'];url=_url(cik,doc['metadata'])
            _require(ref.get('status')=='ready' and ref.get('source_url')==url and _fresh(ref.get('observed_at'),as_of))
            _require(isinstance(encoded,str) and 0<len(encoded)<=4*((MAX_FILING_BYTES+2)//3))
            raw=base64.b64decode(encoded,validate=True)
            total+=len(raw);_require(total<=MAX_SCOPE_BYTES)
            _require(0<len(raw)<=MAX_FILING_BYTES and hashlib.sha256(raw).hexdigest()==ref.get('payload_sha256'))
            body_sha=hashlib.sha256(_bound_body(raw,doc.get('normalization'))).hexdigest()
            _require(body_sha==doc.get('body_sha256',doc['sha256']))
            item=dict(role=role,**doc['metadata'],source_ref=url,observed_at=ref['observed_at'],payload_sha256=ref['payload_sha256'],body_sha256=body_sha,binding_normalization=doc.get('normalization','identity_bytes'),reference_capture_sha256=doc['sha256'])
            parsed=None;source_refs=None;extra=None;companion=companion_source(doc,url)
            if companion is not None:
                c,curl=companion;cref=ref['companion'];_require(p['kind']=='supported_common' and role in {'annual','cover'})
                _require(cref.get('status')=='ready' and cref.get('source_url')==curl and _fresh(cref.get('observed_at'),as_of))
                encoded=cref['payload_raw_base64'];_require(isinstance(encoded,str) and 0<len(encoded)<=4*((MAX_FILING_BYTES+2)//3))
                craw=base64.b64decode(encoded,validate=True);total+=len(craw)
                _require(0<len(craw)<=MAX_FILING_BYTES and total<=MAX_SCOPE_BYTES and hashlib.sha256(craw).hexdigest()==cref.get('payload_sha256'))
                cbody=hashlib.sha256(_bound_body(craw,c.get('normalization'))).hexdigest();_require(cbody==c.get('body_sha256',c['sha256']))
                parsed,source_refs=bind_document_set(raw,craw,url=url,companion_url=curl,href=c['href'])
                extra=dict(item,role=role+'_companion',form=c['document_type'],parent_form=doc['metadata']['form'],primaryDocument=c['primaryDocument'],source_ref=curl,parent_source_ref=url,parent_href=c['href'],observed_at=cref['observed_at'],payload_sha256=cref['payload_sha256'],body_sha256=cbody,binding_normalization=c.get('normalization','identity_bytes'),reference_capture_sha256=c['sha256'])
            else:_require('companion' not in ref)
            if p['kind']=='supported_common':
                root,ns,contexts,common,other=_cover(raw,cik,doc['metadata'],doc,url,parsed=parsed,source_refs=source_refs);_require(common['ticker']==ticker)
                item.update(selected_common=common,raw_cover_observations=other)
                if role=='annual':
                    eps=_original_eps(raw,cik,doc['metadata']['reportDate'],url,parsed=parsed,source_refs=source_refs)
                    ids={n.get('id'):n for n in root.iter() if n.get('id')}
                    for identity in p['basis_fact_ids']:
                        n=ids[identity];uri,name=_qname(n.get('name'),ns)
                        _require(_taxonomy(uri)=='us-gaap' and name in {'CommonStockParOrStatedValuePerShare','StockholdersEquityNoteDisclosureTextBlock','EarningsPerSharePolicyTextBlock','ScheduleOfEarningsPerShareBasicAndDilutedTableTextBlock'} and n.get('contextRef') in contexts)
                        _require(bool(''.join(n.itertext()).strip()))
                        basis.append(dict(concept=name,source_ref=source_refs[identity] if source_refs is not None else url+'#'+identity,context_id=n.get('contextRef')))
            if doc.get('inspection_observations'):
                _require(p['kind']=='inspection_only' and companion is None)
                observations.extend(dict(o,role=role,observed_at=ref['observed_at'],publication_date=doc['metadata']['filingDate'],accession=doc['metadata']['accessionNumber'],rights_status=RIGHTS) for o in inspect_observations(raw,cik=cik,metadata=doc['metadata'],url=url,contracts=doc['inspection_observations']))
            documents.append(item)
            if extra is not None:documents.append(extra)
        result=dict(status=p['kind'],reason=p['reason'],policy_id=p['policy_id'],ticker=ticker,sec_cik=cik,issuer_symbols=p['issuer_symbols'],unassigned_issuer_symbols=[s for s in p['issuer_symbols'] if s!=ticker],documents=documents,basis_refs=basis,evidence_observations=observations,alias_mappings_established=False,technical_interpretation_only=True,commercial_eligible=False,rights_status=RIGHTS)
        if p['kind']=='supported_common':_require(eps is not None);result['original_eps']=eps
        return result
    except (ValueError,KeyError,TypeError,AttributeError,OverflowError,RecursionError,binascii.Error,ET.ParseError):return held
