"""Synthetic linked filing sources with independently located facts/resources."""
import base64,hashlib,re
from selected_security_fixtures import fixture


def document_set_fixture(kind='financial'):
    policy,row,packet,raw=fixture()
    roles=['annual'] if kind=='financial' else ['annual','cover']
    for role in roles:
        original=raw[role];opening=original[:original.index(b'>')+1]
        pattern=(rb'<x:context\b.*?</x:context>|<x:unit\b.*?</x:unit>|<ix:nonFraction\b.*?</ix:nonFraction>|<ix:nonNumeric id="note".*?</ix:nonNumeric>'
                 if kind=='financial' else rb'<ix:nonNumeric id="(?:title|symbol|exchange)".*?</ix:nonNumeric>')
        moved=b''.join(re.findall(pattern,original));name=role+'-linked.htm'
        raw[role]=re.sub(pattern,b'',original).replace(b'</html>',b'<a href="'+name.encode()+b'">Incorporated source</a></html>')
        raw[role+'-companion']=opening+moved+b'</html>'
        doc=policy['documents'][role]
        doc['sha256']=hashlib.sha256(raw[role]).hexdigest()
        doc['companion']=dict(primaryDocument=name,href=name,document_type='EX-13' if kind=='financial' else 'EX-99.01',sha256=hashlib.sha256(raw[role+'-companion']).hexdigest())
        ref=packet['documents'][role];ref.update(payload_sha256=doc['sha256'],payload_raw_base64=base64.b64encode(raw[role]).decode())
        ref['companion']=dict(status='ready',source_url=ref['source_url'].rsplit('/',1)[0]+'/'+name,observed_at=ref['observed_at'],payload_sha256=doc['companion']['sha256'],payload_raw_base64=base64.b64encode(raw[role+'-companion']).decode())
    return policy,row,packet,raw


def reseal(policy,packet,raw,role='annual',companion=False):
    key=role+'-companion' if companion else role
    doc=policy['documents'][role];ref=packet['documents'][role]
    if companion:doc=doc['companion'];ref=ref['companion']
    sha=hashlib.sha256(raw[key]).hexdigest();doc['sha256']=sha
    ref.update(payload_sha256=sha,payload_raw_base64=base64.b64encode(raw[key]).decode())
