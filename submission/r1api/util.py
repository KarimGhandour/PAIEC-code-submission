import json,hashlib,unicodedata
from pathlib import Path
def canonical_json(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def sha(obj):
    return hashlib.sha256(canonical_json(obj).encode()).hexdigest()

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def content_hash(text):
    if not isinstance(text,str):text=''
    return hashlib.sha256(' '.join(unicodedata.normalize('NFKC',text or '').casefold().split()).encode()).hexdigest()

def features(text):
    if not isinstance(text,str):return {}
    return dict(piece.split('=',1) for piece in (text or '').split(';') if '=' in piece)
