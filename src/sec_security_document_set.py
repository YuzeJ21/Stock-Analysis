"""Bounded same-accession resources; never a raw-response replacement or fetcher."""
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit,urljoin
from src.sec_inline_filing import _tree,X,IX,MAX_ELEMENTS
from src.sec_exact_filing import MAX_FILING_BYTES

MAX_SCOPE_BYTES=64*1024*1024


def companion_source(doc,url):
    if 'companion' not in doc:return None
    c=doc['companion']
    if not isinstance(c,dict) or c.get('document_type') not in {'EX-13','EX-99.01'}:raise ValueError('unsupported_companion')
    name=c.get('primaryDocument');href=c.get('href')
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,198}\.htm',name) or '..' in name:raise ValueError('unsafe_companion_filename')
    if not isinstance(href,str) or not re.fullmatch(re.escape(name)+r'(?:#[A-Za-z0-9_.:-]{1,200})?',href):raise ValueError('unsafe_companion_link')
    target=url.rsplit('/',1)[0]+'/'+name
    if target==url or urljoin(url,href).split('#')[0]!=target:raise ValueError('companion_identity_conflict')
    return c,target


def bind_document_set(raw,companion_raw,*,url,companion_url,href):
    """Parse only two supplied bodies, retaining a URL for each original ID."""
    if any(not isinstance(b,bytes) or not 0<len(b)<=MAX_FILING_BYTES for b in (raw,companion_raw)) or len(raw)+len(companion_raw)>MAX_SCOPE_BYTES:raise ValueError('unbounded_document_set')
    parts=[urlsplit(u) for u in (url,companion_url)]
    pattern=r'/Archives/edgar/data/[1-9]\d{0,9}/\d{18}/[A-Za-z0-9_.-]+\.htm'
    if any(p.scheme!='https' or p.netloc!='www.sec.gov' or p.query or p.fragment or not re.fullmatch(pattern,p.path) for p in parts):raise ValueError('invalid_document_set_url')
    if parts[0].path.rsplit('/',1)[0]!=parts[1].path.rsplit('/',1)[0] or url==companion_url or urljoin(url,href).split('#')[0]!=companion_url:raise ValueError('mixed_document_set')
    trees=[_tree(raw),_tree(companion_raw)];namespaces={};sources={};ids={};count=0
    for (root,ns),source in zip(trees,(url,companion_url)):
        for prefix,uri in ns.items():
            if prefix in namespaces and namespaces[prefix]!=uri:raise ValueError('document_set_namespace_conflict')
            namespaces[prefix]=uri
        for node in root.iter():
            count+=1
            if count>MAX_ELEMENTS or node.get('{http://www.w3.org/XML/1998/namespace}base') is not None or node.tag.rsplit('}',1)[-1]=='base':raise ValueError('document_set_resource_scope')
            identity=node.get('id')
            if identity:
                if identity in ids:raise ValueError('document_set_duplicate_id')
                ids[identity]=node;sources[identity]=source+'#'+identity
    if not any(node.get('href')==href for node in trees[0][0].iter() if node.tag.rsplit('}',1)[-1]=='a'):raise ValueError('companion_not_declared')
    for root,_ in trees:
        for node in root.iter():
            if not node.tag.startswith('{'+IX+'}'):continue
            if node.get('target') not in {None,''}:raise ValueError('multiple_inline_targets')
            for attr,tag in (('contextRef','context'),('unitRef','unit')):
                ref=node.get(attr)
                if ref is not None and (ref not in ids or ids[ref].tag!='{'+X+'}'+tag):raise ValueError('missing_document_set_resource')
    union=ET.Element('validated-document-set')
    for root,_ in trees:union.append(root)
    return (union,namespaces),sources
