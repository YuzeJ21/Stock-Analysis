"""Read-only, exact-source security observations, never valuation inputs.

Call only after metadata, URL, raw/body digest and freshness validation. The
HTML path locates prose only; it cannot supply inline facts or financial values.
"""
from collections.abc import Mapping
import hashlib
from html.parser import HTMLParser
import re

from src.sec_inline_filing import X,IX,ISO,MAX_ELEMENTS,_tree,_qname,_number
from src.company_sec_online_preview import _iso_date
from src.sec_exact_filing import MAX_FILING_BYTES

H='http://www.w3.org/1999/xhtml'
D='http://xbrl.org/2006/xbrldi'


def _need(value):
    if not value:raise ValueError('security_observation_unverified')


def _text(node):return ' '.join(''.join(node.itertext()).split())
def _sha(text):return hashlib.sha256(text.encode()).hexdigest()


class _Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.active=[];self.count=0;self.size=0
    def handle_starttag(self,tag,attrs):
        self.count+=1;_need(self.count<=MAX_ELEMENTS)
        if tag=='p':self.rows.append([]);self.active.append(len(self.rows)-1)
    def handle_endtag(self,tag):
        if tag=='p' and self.active:self.active.pop()
    def handle_data(self,data):
        self.size+=len(data);_need(self.size<=MAX_FILING_BYTES)
        for i in self.active:self.rows[i].append(data)


def _context(ids,ns,c,metadata):
    _need(c['context_id'] in ids)
    node=ids[c['context_id']];_need(node.tag==f'{{{X}}}context' and len(node)==2)
    entity,period=node.find(f'{{{X}}}entity'),node.find(f'{{{X}}}period')
    _need(entity is not None and period is not None and len(period)==2)
    ident=entity.find(f'{{{X}}}identifier');dims=c['dimensions']
    _need(ident is not None and len(ident)==0 and ident.get('scheme')=='http://www.sec.gov/CIK' and ident.text==c['entity_cik'])
    _need(len(entity)==(2 if dims else 1))
    segment=entity.find(f'{{{X}}}segment');actual=[]
    if dims:
        _need(segment is not None and len(segment)==len(dims))
        for member in segment:
            _need(member.tag==f'{{{D}}}explicitMember' and len(member)==0)
            actual.append([*_qname(member.get('dimension'),ns),*_qname(member.text,ns)])
    _need(actual==dims)
    first,last=period.find(f'{{{X}}}startDate'),period.find(f'{{{X}}}endDate')
    _need(first is not None and last is not None and len(first)==len(last)==0)
    start,end=first.text,last.text
    _need(start==c['period_start'] and end==c['period_end']==metadata['reportDate'] and _iso_date(start) and _iso_date(end) and start<=end)
    return dict(entity_cik=ident.text,period_start=start,period_end=end,dimensions=actual,context_id=c['context_id'])


def _unit(ids,ns,c):
    _need(c['unit_id'] in ids)
    node=ids[c['unit_id']];_need(node.tag==f'{{{X}}}unit' and len(node)==1 and node[0].tag==f'{{{X}}}divide' and len(node[0])==2)
    numerator=node[0].find(f'{{{X}}}unitNumerator');denominator=node[0].find(f'{{{X}}}unitDenominator')
    _need(numerator is not None and denominator is not None and len(numerator)==len(denominator)==1)
    _need(numerator[0].tag==denominator[0].tag==f'{{{X}}}measure' and len(numerator[0])==len(denominator[0])==0)
    _need(_qname(numerator[0].text,ns)==(ISO,c['currency']) and _qname(denominator[0].text,ns)==(X,'shares'))
    return c['currency']+'/shares'


def _location(root,path):
    parts=re.findall(r'/([a-z][a-z0-9]*)\[([1-9][0-9]{0,5})\]',path)
    _need(parts and ''.join(f'/{tag}[{n}]' for tag,n in parts)==path)
    _need(parts[0]==('html','1') and root.tag==f'{{{H}}}html');node=root
    for tag,n in parts[1:]:
        matches=node.findall(f'{{{H}}}'+tag);_need(int(n)<=len(matches));node=matches[int(n)-1]
    return node


def inspect_observations(raw,*,cik,metadata,url,contracts):
    _need(isinstance(raw,bytes) and 0<len(raw)<=MAX_FILING_BYTES and isinstance(contracts,list) and 0<len(contracts)<=16)
    _need(b'<!doctype' not in raw.lower() and b'<!entity' not in raw.lower() and b'\x00' not in raw)
    root=ns=ids=paragraphs=None;result=[]
    for c in contracts:
        _need(isinstance(c,Mapping));kind=c['kind']
        o=dict(kind=kind,label=c['label'],source_ref=url,filing_cik=cik,financial_eligible=False)
        if kind=='html_paragraph':
            if paragraphs is None:
                parser=_Paragraphs();parser.feed(raw.decode('utf-8-sig'));parser.close()
                paragraphs=[' '.join(''.join(p).split()) for p in parser.rows]
            n=c['paragraph_ordinal'];_need(type(n) is int and 0<n<=len(paragraphs))
            _need(_sha(paragraphs[n-1])==c['text_sha256'])
            o.update(location=f'p[{n}]',text_sha256=c['text_sha256'])
        else:
            if root is None:root,ns=_tree(raw);ids={n.get('id'):n for n in root.iter() if n.get('id')}
            if kind=='element_note':
                node=_location(root,c['path']);_need(_sha(_text(node))==c['text_sha256'])
                o.update(location=c['path'],text_sha256=c['text_sha256'])
                if c.get('extract') is not None:
                    _need(c['extract']=='ads_common_ratio')
                    matches=re.findall(r'each ADS represents [A-Za-z]+ \(([1-9][0-9]{0,3})\) common shares',_text(node),re.I)
                    _need(len(matches)==1)
                    o.update(value=int(matches[0]),unit='ordinary_shares/ADS')
            else:
                _need(kind in {'numeric','note'} and c['fact_id'] in ids);node=ids[c['fact_id']]
                _need(_qname(node.get('name'),ns)==(c['namespace_uri'],c['concept']) and node.get('contextRef')==c['context_id'])
                _need(node.get('target') in {None,''} and node.get('tupleRef') is None and node.get('{http://www.w3.org/2001/XMLSchema-instance}nil') in {None,'false','0'})
                o.update(_context(ids,ns,c,metadata),concept=c['concept'],namespace_uri=c['namespace_uri'],source_ref=url+'#'+c['fact_id'],context_source_ref=url+'#'+c['context_id'])
                if kind=='numeric':
                    _need(node.tag==f'{{{IX}}}nonFraction' and node.get('unitRef')==c['unit_id'])
                    numeric,reason=_number(node,ns);_need(not reason and numeric is not None)
                    o.update(numeric,unit=_unit(ids,ns,c),unit_source_ref=url+'#'+c['unit_id'],security_basis=c['security_basis'],currency_basis=c['currency_basis'])
                else:
                    _need(node.tag==f'{{{IX}}}nonNumeric');chain=[node];seen={c['fact_id']}
                    _need(isinstance(c['continuations'],list) and len(c['continuations'])<=8)
                    for identity in c['continuations']:
                        _need(chain[-1].get('continuedAt')==identity and identity not in seen and identity in ids)
                        tail=ids[identity];_need(tail.tag==f'{{{IX}}}continuation' and tail.get('target') in {None,''})
                        chain.append(tail);seen.add(identity)
                    _need(chain[-1].get('continuedAt') is None)
                    hashes=[_sha(_text(n)) for n in chain]
                    if 'text_sha256' in c:_need(hashes==c['text_sha256'])
                    o.update(source_refs=[url+'#'+n.get('id') for n in chain],text_sha256=hashes)
        result.append(o)
    return result
