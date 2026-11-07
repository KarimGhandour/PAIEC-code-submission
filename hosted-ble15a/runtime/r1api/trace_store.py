"""Read exact released trace rows from a losslessly derived stdlib asset."""
from functools import lru_cache
import hashlib,json,sqlite3,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data'
EXPECTED='67459dbde2cd90cb6ee923f740162985545c2b24d5255e2efc6c6e38533ad7ac'
@lru_cache(maxsize=1)
def verified_path():
 p=ROOT/'traces_chunked.sqlite'
 with p.open('rb')as s:
  if hashlib.file_digest(s,'sha256').hexdigest()!=EXPECTED:raise PermissionError('Trace store integrity')
 return p

def read_records(family,ids):
 if not ids:return[]
 c=sqlite3.connect('file:'+str(verified_path())+'?mode=ro',uri=True)
 try:
  selected=c.execute('select position,chunk,offset from lookup where family=? and response_id in('+','.join('?'for _ in ids)+') order by position',[family,*ids]).fetchall()
  blocks={};out=[]
  for pos,chunk,offset in selected:
   if chunk not in blocks:
    blob=c.execute('select body from chunks where family=? and chunk=?',(family,chunk)).fetchone()[0]
    raw=zlib.decompress(blob)
    if len(raw)>20000000:raise PermissionError('Trace chunk bound')
    blocks[chunk]=json.loads(raw)
   row=dict(blocks[chunk][offset]);v=row.get('r1_full_trace_sha256')
   if v is not None:row['r1_full_trace_sha256']=bytes.fromhex(v)
   out.append(row)
  return out
 finally:c.close()
