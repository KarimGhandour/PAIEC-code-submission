"""Eight real local BLE retrieval operations with a controller-enforced cold-start view."""
import json,math,re,sqlite3,time
from functools import lru_cache
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from .util import content_hash,sha,file_sha
from .semantic import encode
from .assets import hydrated_corpus
RUN=Path(__file__).resolve().parents[1]/'data'
FROZEN_CORPUS_SHA='f3a88eb32fe3128ce2d4f21a6493b6553b9fad5ae92646b1bb7587058bc10384'
FROZEN_POLICY_SHA='5359ad08d02fa684e82dfe45960b9b5800d405b3ebd65db9b4d3be279ead5d77'
FROZEN_PROTECTED_FILE_SHA='26ec64c9bdcc2ef301fddf345f27109069e9808497340ab2dd4069699db217ed'
FROZEN_EXCLUDED_SHA='e3b47e901d4942ea39c5cd5c73056b7d387821e8d3fd03eeba4407eca95c3811'
FROZEN_PROTECTED_INPUTS_SHA='90cdda60dd3ae1c6ea231db8d84fb070aaf47644682ef5556f37d5a5ff04e3f8'
FROZEN_BLOCKED_IDS_SHA='5624a7f51f1972b2a1ef10181198f27c42dc5361043a7f6b466c5a16c4a26d2b'

@lru_cache(maxsize=2)
def _verified_corpus(path,inode,size,mtime_ns,ctime_ns,expected):
 # A whole-file SHA is paid once per process; the packaged file's stat identity
 # is rechecked on every forecast. The cache is never used for a different file.
 if file_sha(path)!=expected:raise PermissionError('Corpus hash differs from frozen firewall cache')
 return True

def _static_firewall(cache_path,targets,excluded_families,policy,path):
 cache_path=Path(cache_path)
 if not cache_path.is_file():raise PermissionError('Frozen firewall cache missing')
 cache=json.loads(cache_path.read_text())
 if cache.get('format')!='paiec-r1-firewall-v1':raise PermissionError('Unknown firewall cache format')
 if (cache.get('corpus_sha256')!=FROZEN_CORPUS_SHA or
     cache.get('policy_file_sha256')!=FROZEN_POLICY_SHA or
     cache.get('protected_file_sha256')!=FROZEN_PROTECTED_FILE_SHA or
     cache.get('excluded_file_sha256')!=FROZEN_EXCLUDED_SHA or
     cache.get('protected_inputs_sha256')!=FROZEN_PROTECTED_INPUTS_SHA or
     cache.get('blocked_ids_sha256')!=FROZEN_BLOCKED_IDS_SHA):
  raise PermissionError('Firewall cache differs from frozen scientific source')
 protected=cache.get('protected_count')
 if type(protected) is not int or protected<1 or len(targets)<protected:raise PermissionError('Protected input count mismatch')
 if sha(targets[:protected])!=cache.get('protected_inputs_sha256'):raise PermissionError('Protected input manifest mismatch')
 if file_sha(RUN/'protected_inputs.json')!=cache.get('protected_file_sha256'):raise PermissionError('Protected input file changed')
 if file_sha(RUN/'active_permission_policy.json')!=cache.get('policy_file_sha256'):raise PermissionError('Eligibility policy changed')
 if file_sha(Path(__file__).parent/'excluded_families.json')!=cache.get('excluded_file_sha256'):raise PermissionError('Exclusion list changed')
 if sorted(set(excluded_families)|set(policy['quarantined_inventory_matches']))!=cache.get('blocked_families'):raise PermissionError('Blocked family set changed')
 if sha(cache.get('blocked_ids'))!=cache.get('blocked_ids_sha256'):raise PermissionError('Blocked ID snapshot damaged')
 st=path.stat()
 if st.st_size!=cache.get('corpus_size'):raise PermissionError('Corpus size changed')
 _verified_corpus(str(path),st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,cache['corpus_sha256'])
 after=path.stat()
 if (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)!=(st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns):
  raise PermissionError('Corpus changed during verification')
 return cache,targets[protected:]

def tokens(text):return re.findall(r'[^\W_]+',str(text).lower(),flags=re.UNICODE)
def match_query(text):
 words=[t for t in tokens(text) if len(t)>2];words=list(dict.fromkeys(words))[:20]
 return ' OR '.join('"'+w.replace('"','""')+'"' for w in words)
def shingles(text):
 ws=tokens(text);return {tuple(ws[i:i+5]) for i in range(max(0,len(ws)-4))}

def similarity_kind(subject,target):
 keys=['normalized_name','provider','release_date','access_date','harness','harness_version','reasoning_effort','subject_features_extra']
 a=lambda s:re.sub('[^a-z0-9]','',str(s.get('normalized_name') or '').lower())
 if all(subject.get(k)==target.get(k) for k in keys):return '1 exact visible model/configuration'
 if a(subject) and a(subject)==a(target):return '2 exact named model, configuration differences/unknowns'
 if subject.get('provider') and subject.get('provider')==target.get('provider'):return '4 same provider; different model, weak evidence'
 return '5 weak peer evidence; no established version/configuration equivalence'

class AuditedDB:
 def __init__(self,excluded_families=(),targets=(),target_subject=None,quality=False,path=None,static_cache=False):
  self.path=Path(path or hydrated_corpus());self.c=sqlite3.connect('file:'+str(self.path)+'?mode=ro',uri=True);self.c.row_factory=sqlite3.Row
  self.c.execute('pragma cache_size=-64000');self.c.executescript('create temp table blocked_families(family text primary key);create temp table blocked_ids(id integer primary key);')
  policy=json.loads((RUN/'active_permission_policy.json').read_text());original_exclusions=excluded_families;excluded_families=set(excluded_families)|set(policy['quarantined_inventory_matches'])
  self.c.executemany('insert into blocked_families values(?)',[(f,) for f in sorted(set(excluded_families))]);self.target_subject=target_subject or {};self.quality=quality;self.events=[];self.target_shingles=[];self.semantic=None
  self.targets=targets
  if static_cache:
   cache,targets=_static_firewall(RUN/'firewall_static_cache.json',targets,original_exclusions,policy,self.path)
   self.c.executemany('insert into blocked_ids values(?)',[(i,) for i in cache['blocked_ids']])
   for t in self.targets[:cache['protected_count']]:
    inp=t.get('input',t);text=inp[1]['item_content'] if isinstance(inp,list) else str(inp);v=shingles(text)
    if len(v)>=10:self.target_shingles.append(v)
  for t in targets:
   inp=t.get('input',t);text=inp[1]['item_content'] if isinstance(inp,list) else str(inp);h=content_hash(text);v=shingles(text)
   if len(v)>=10:self.target_shingles.append(v)
   ids=list(self.c.execute('select id from items where content_hash=?',(h,)))
   if isinstance(t,dict):
    if t.get('source_group'):ids+=list(self.c.execute('select id from items where family=? and source_group=?',(t.get('family',''),t['source_group'])))
    if t.get('item_id'):
     # Released join keys only enforce exclusions; never reverse-map a runtime anonymous benchmark id.
     ids+=list(self.c.execute('select id from items where family=? and iid=?',(t.get('family',''),t['item_id'])))
   self.c.executemany('insert or ignore into blocked_ids values(?)',[(r[0],) for r in ids])
   rare_words=sorted({w for w in tokens(text) if len(w)>4 and not re.fullmatch(r'[a-f0-9]{20,}',w)},key=lambda w:(-len(w),w))[:12]
   q=match_query(' '.join(rare_words))
   if q:
    for r in self.c.execute('select i.id,i.content,i.source_key from item_fts join items i on i.id=item_fts.rowid where item_fts match ? order by rank limit 100',(q,)):
     if self._near(r['content']):self._block(r['id'])
   # Exact source-key equivalence is shared across families, including whole repositories.
   source_keys=[r[0] for r in self.c.execute('select distinct source_key from items where id in(select id from blocked_ids) and source_key!=""')]
   for sk in source_keys:self.c.execute('insert or ignore into blocked_ids select id from items where source_key=?',(sk,))
  self.c.executescript('''create temp view permitted_items as select * from items where family not in(select family from blocked_families) and id not in(select id from blocked_ids);''')
  self.blocked_count=self.c.execute('select count(*) from blocked_ids').fetchone()[0];self.sealed_firewall=True
 def close(self):self.c.close()
 def _block(self,i):
  if getattr(self,'sealed_firewall',False) and not self.c.execute('select 1 from blocked_ids where id=?',(i,)).fetchone():raise PermissionError('Previously undetected protected near-duplicate; stop before returning evidence')
  self.c.execute('insert or ignore into blocked_ids values(?)',(i,))
 def _near(self,text):
  v=shingles(text)
  if len(v)<10:return False
  return any(min(len(v),len(o))>=.75*max(len(v),len(o)) and len(v&o)/max(1,len(v|o))>=.85 for o in self.target_shingles)
 def _family(self,f):
  f=str(f).replace('/formatted_tables','')
  if self.c.execute('select 1 from blocked_families where family=?',(f,)).fetchone():return None
  if self.c.execute('select 1 from benchmarks where family=?',(f,)).fetchone():return f
  for r in self.c.execute('select family,card from benchmarks where family not in(select family from blocked_families)'):
   if json.loads(r['card']).get('benchmark_id')==f:return r['family']
  return None
 def _safe_item(self,f,iid):
  r=self.c.execute('select * from permitted_items where family=? and iid=?',(f,str(iid))).fetchone()
  if r and self._near(r['content']):self._block(r['id']);return None
  return r
 def _emit(self,kind,data,started):
  text=json.dumps({'tool':kind,'evidence':data},ensure_ascii=False,default=str)
  # Evidence is untrusted data and never an instruction to the model.
  text=re.sub(r'/Users/[^\s\"\']+','[local path redacted]',text)
  if len(text)>64000:raise ValueError('Evidence exceeds compact packet bound')
  self.events.append({'tool':kind,'payload_sha256':sha(text),'bytes':len(text.encode()),'elapsed_seconds':time.monotonic()-started,'evidence':data})
  return text
 def _item_card(self,r,preview=400):
  st=self.c.execute('select * from item_statistics where family=? and iid=?',(r['family'],r['iid'])).fetchone()
  card={'benchmark_id':r['family'],'item_id':r['iid'],'content':r['content'][:preview],'shown_chars':min(preview,len(r['content'])),'full_chars':len(r['content']),'content_truncated':len(r['content'])>preview,'historical_mean_score':float(st['k']/st['n']) if st and st['n'] else None,'observed_trials':st['n'] if st else 0,'subjects':st['subjects'] if st else 0}
  if self.quality:card.update(evidence_tier='E2',item_context_tier='E1' if r['complete'] else 'E2',context_complete=bool(r['complete']),limits='Historical mean mixes model capability and item difficulty; not a target probability. Repeated trials are not independent items.',source_group=r['source_group'],content_hash=r['content_hash'],features=r['features'])
  return card
 def search_benchmarks(self,query,k=10):
  start=time.monotonic();q=match_query(query);rows=[]
  if q:
   for r in self.c.execute('select b.family,b.card from benchmark_fts f join benchmarks b on b.family=f.family where benchmark_fts match ? and b.family not in(select family from blocked_families) order by rank limit ?',(q,k)):
    b=json.loads(r['card']);rows.append({'benchmark_id':r['family'],'name':b.get('name'),'description':str(b.get('description') or '')[:350],'domain':b.get('domain'),'modality':b.get('modality')})
  return self._emit('search_benchmarks',rows,start)
 def get_benchmark(self,benchmark_id):
  start=time.monotonic();f=self._family(benchmark_id)
  if not f:return self._emit('get_benchmark',{'status':'excluded_or_unavailable'},start)
  row=self.c.execute('select card,source,license from benchmarks where family=?',(f,)).fetchone();b=json.loads(row['card']);b.pop('saturation',None)
  b['benchmark_id']=f;b['available_admitted_items']=self.c.execute('select count(*) from permitted_items where family=?',(f,)).fetchone()[0];b['actual_local_traces']=bool(self.c.execute('select 1 from trace_catalog where family=?',(f,)).fetchone());b['source_provenance']=row['source'];b['original_license']=row['license'];b['aggregate_warning']='Raw published saturation omitted; filtered measurements available through get_scores.'
  return self._emit('get_benchmark',b,start)
 def find_model(self,model_name):
  start=time.monotonic();norm=re.sub('[^a-z0-9]','',str(model_name).lower());rows=[]
  if norm:
   for r in self.c.execute('select * from subjects where family not in(select family from blocked_families) and (normalized like ? or lower(name) like ?) order by family,name limit 40',('%'+norm+'%','%'+str(model_name).lower()+'%')):
    s=json.loads(r['config']);card={'benchmark_id':r['family'],'subject_id':r['sid'],'model':r['name'],'provider':r['provider'],'harness':r['harness'],'configuration':{k:s.get(k) for k in ['release_date','access_date','harness_version','reasoning_effort','subject_features_extra']}}
    if self.quality:card['compatibility']=similarity_kind(s,self.target_subject)
    rows.append(card)
  return self._emit('find_model',rows,start)
 def get_scores(self,benchmark_id,model='',test_condition=''):
  start=time.monotonic();f=self._family(benchmark_id)
  if not f:return self._emit('get_scores',{'status':'excluded_or_unavailable'},start)
  norm=re.sub('[^a-z0-9]','',model.lower());params=[f];where='s.family=?'
  if model:where+=' and (s.normalized like ? or lower(s.name) like ?)';params+=['%'+norm+'%','%'+model.lower()+'%']
  if test_condition:where+=' and a.cond=?';params+=[test_condition]
  # If protected source duplicates affect this family, recompute from filtered rows, never leak via cached aggregates.
  blocked=self.c.execute('select 1 from items where family=? and id in(select id from blocked_ids) limit 1',(f,)).fetchone()
  source='subject_statistics'
  if blocked:
   self.c.execute('drop table if exists temp.filtered_stats');self.c.execute('''create temp table filtered_stats as select family,sid,cond,sum(n) n,sum(k) k,sum(items) items,count(*) source_groups,sum(k/n) group_sum,sum((k/n)*(k/n)) group_square from (select p.family,p.sid,p.cond,i.source_group,sum(p.n) n,sum(p.k) k,count(distinct p.iid) items from pair_stats p join permitted_items i on p.family=i.family and p.iid=i.iid where p.family=? group by p.family,p.sid,p.cond,i.source_group) group by family,sid,cond''',(f,));source='filtered_stats'
  sql=f'select a.*,s.name,s.config from {source} a join subjects s on a.family=s.family and a.sid=s.sid where {where} order by a.n desc,s.name limit 40';cards=[]
  for r in self.c.execute(sql,params):
   card={'benchmark_id':f,'subject_id':r['sid'],'model':r['name'],'test_condition':r['cond'],'mean_score':r['k']/r['n'],'successes':r['k'],'trials':r['n'],'distinct_items':r['items'],'independent_source_groups':r['source_groups'],'repeated_or_group_related_trials':r['n']-r['source_groups']}
   if self.quality:
    g=r['source_groups'];m=r['group_sum']/g;var=max(0,(r['group_square']-g*m*m)/max(1,g-1));se=math.sqrt(var/g)
    card.update(group_balanced_mean=m,smoothed_group_mean=(4+r['group_sum'])/(8+g),descriptive_cluster_mean_95=[max(0,m-1.96*se),min(1,m+1.96*se)],configuration=json.loads(r['config']),compatibility=similarity_kind(json.loads(r['config']),self.target_subject),uncertainty_caveat='Normal interval over independent recorded source-group rates; descriptive and unreliable for very few groups. Not a posterior on the target item.')
   cards.append(card)
  return self._emit('get_scores',cards,start)
 def search_items(self,benchmark_id,query,k=8):
  start=time.monotonic();f=self._family(benchmark_id);q=match_query(query);out=[]
  if f and q:
   for r in self.c.execute('select i.* from item_fts join permitted_items i on i.id=item_fts.rowid where item_fts match ? and i.family=? order by rank limit ?',(q,f,k*3)):
    if self._near(r['content']):self._block(r['id']);continue
    out.append(self._item_card(r))
    if len(out)>=k:break
  return self._emit('search_items',out,start)
 def get_item(self,benchmark_id,item_id='',sample=0,model=''):
  start=time.monotonic();f=self._family(benchmark_id);out=[]
  if not f:return self._emit('get_item',{'status':'excluded_or_unavailable'},start)
  if item_id:
   r=self._safe_item(f,item_id);rows=[r] if r else []
  else:rows=self.c.execute('select * from permitted_items where family=? order by content_hash limit ?',(f,min(max(int(sample or 1),1),5))).fetchall()
  for r in rows:
   if self._near(r['content']):self._block(r['id']);continue
   card=self._item_card(r,6000);card['released_reference']=r['reference'];card['features']=r['features']
   if model:
    norm=re.sub('[^a-z0-9]','',model.lower());card['model_measurements']=[dict(x) for x in self.c.execute('select s.name,p.n trials,p.k successes,p.cond test_condition from pair_stats p join subjects s on s.family=p.family and s.sid=p.sid where p.family=? and p.iid=? and (s.normalized like ? or lower(s.name) like ?) limit 20',(f,r['iid'],'%'+norm+'%','%'+model.lower()+'%'))]
   out.append(card)
  return self._emit('get_item',out if out else {'status':'excluded_or_unavailable'},start)
 def get_trace(self,benchmark_id,model,item_id):
  start=time.monotonic();f=self._family(benchmark_id)
  if not f or not self._safe_item(f,item_id):return self._emit('get_trace',{'status':'excluded_or_unavailable'},start)
  trace=self.c.execute('select * from trace_catalog where family=?',(f,)).fetchone()
  if not trace:return self._emit('get_trace',{'status':'no_released_local_trace'},start)
  norm=re.sub('[^a-z0-9]','',model.lower());rs=self.c.execute('select p.example_response,s.name from pair_stats p join subjects s on p.family=s.family and p.sid=s.sid where p.family=? and p.iid=? and (s.normalized like ? or lower(s.name) like ?) limit 3',(f,item_id,'%'+norm+'%','%'+model.lower()+'%')).fetchall()
  if not rs:return self._emit('get_trace',{'status':'no_matching_model_attempt'},start)
  ids=[r['example_response'] for r in rs];tab=pq.read_table(str(RUN/'traces'/(f+'.parquet')),filters=[('response_id','in',ids)]);out=[]
  for r in tab.to_pylist()[:2]:
   txt=str(r.get('trace') or '');out.append({'benchmark_id':f,'item_id':item_id,'response_id':r['response_id'],'model':next(x['name'] for x in rs if x['example_response']==r['response_id']),'trace':txt[:4000],'trace_truncated':(r['r1_full_trace_chars'] or len(txt))>4000,'full_trace_sha256':(r['r1_full_trace_sha256'] or bytes.fromhex(sha(txt))).hex(),'source':'Actual released local traces.parquet; no synthesized attempt'})
  return self._emit('get_trace',out if out else {'status':'trace_not_present_for_recorded_attempt'},start)
 def semantic_search_items(self,query,k=8,benchmark_id=''):
  start=time.monotonic()
  if self.semantic is None:
   mpath=RUN/'semantic_manifest.json'
   if not mpath.exists():raise FileNotFoundError('Local semantic index not built')
   man=json.loads(mpath.read_text());self.semantic=(np.load(RUN/man['vectors'],mmap_mode='r'),json.loads((RUN/man['items']).read_text()),man)
  from .semantic import representation
  query,_=representation('',{'content':query})
  mat,items,man=self.semantic;vec=encode([query])[0];scores=mat@vec;order=np.argsort(-scores);out=[];seen=set();perfamily=Counter();f=self._family(benchmark_id) if benchmark_id else None
  forbidden={r[0] for r in self.c.execute('select family from blocked_families')};allowed_families=[x for x in man['families'] if x not in forbidden]
  if benchmark_id and not f:return self._emit('semantic_search_items',{'status':'excluded_or_unavailable'},start)
  for ix in order:
   item=items[int(ix)]
   if item['family'] not in allowed_families:continue
   if f and item['family']!=f:continue
   if perfamily[item['family']]>=2:continue
   row=self._safe_item(item['family'],item['iid'])
   if row is None or row['content_hash'] in seen:continue
   card=self._item_card(row);card.update(similarity=float(scores[ix]),backend=man['model'],representation_policy=man['representation_policy']);out.append(card);seen.add(row['content_hash']);perfamily[row['family']]+=1
   if len(out)>=min(max(int(k),1),20):break
  return self._emit('semantic_search_items',{'results':out,'indexed_items':len(items),'indexed_families':allowed_families,'diversity_cap_per_family':2,'similarity_is_not_performance':True},start)
