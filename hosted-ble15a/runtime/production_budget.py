"""Cross-worker atomic USD reservations. Unknown requests keep their reserve."""
from contextlib import contextmanager
from decimal import Decimal,ROUND_CEILING
import json,os,sqlite3,time
from pathlib import Path
from r1api.responses import BudgetError
MAX_REQUESTS=45000
MAX_INFLIGHT=16

def micros(value):return int((Decimal(value)*1000000).to_integral_value(rounding=ROUND_CEILING))
def private_root(config):
 p=Path(config['run_budget_root'])
 if not p.is_absolute():raise BudgetError('Budget root must be absolute')
 p.mkdir(mode=0o700,parents=False,exist_ok=True)
 if p.is_symlink()or p.stat().st_uid!=os.getuid()or p.stat().st_mode&0o077:raise BudgetError('Unsafe shared budget root')
 return p
class ProductionBudget:
 def __init__(self,config,journal):
  self.owned_request_ids=[]
  self.cap=micros(str(config['max_run_usd']));self.journal=journal;self.path=private_root(config)/'ledger.sqlite'
  if self.cap!=50000000 or config.get('spending_policy_id')!='PREPARED_COMPLETION_50_SHARED_V1' or config.get('proposed_total_ceiling_usd')!=50 or config.get('spend_warning_usd')!=40 or self.path.is_symlink():raise BudgetError('Prepared emergency policy identity')
  with self.locked()as c:
   c.execute('create table if not exists meta(id integer primary key,cap integer,held integer,nrequests integer,inflight integer,real integer,fallback integer,full integer,cached integer,consecutive_fallback integer,stopped integer)')
   c.execute('insert or ignore into meta values(1,?,0,0,0,0,0,0,0,0,0)',(self.cap,))
   if c.execute('select cap from meta').fetchone()[0]!=self.cap:raise BudgetError('Budget cap mismatch')
   c.execute('create table if not exists requests(id text primary key,held integer,status text)')
   c.execute('create table if not exists forecasts(id text primary key,status text,p real,genuine integer,full integer,started real)')
 @contextmanager
 def locked(self):
  c=sqlite3.connect(self.path,timeout=30);os.chmod(self.path,0o600)
  try:
   c.execute('pragma busy_timeout=30000');c.execute('pragma synchronous=full');c.execute('begin immediate')
   yield c;c.commit()
  except BaseException:c.rollback();raise
  finally:c.close()
 def reserve(self,request_id,amount):
  # Own the ID before a deadline can interrupt after SQL commit and before logging.
  self.owned_request_ids.append(request_id)
  n=micros(amount)
  if n<=0:raise BudgetError('Non-positive request reservation')
  with self.locked()as c:
   cap,held,count,active,stop=c.execute('select cap,held,nrequests,inflight,stopped from meta').fetchone()
   if stop or held+n>cap or count>=MAX_REQUESTS or active>=MAX_INFLIGHT:raise BudgetError('Aggregate production request/spending limit')
   try:c.execute('insert into requests values(?,?,?)',(request_id,n,'reserved_or_uncertain'))
   except sqlite3.IntegrityError:raise BudgetError('Duplicate request reservation')from None
   c.execute('update meta set held=held+?,nrequests=nrequests+1,inflight=inflight+1',(n,))
  self.journal('run_budget_reserved',{'client_request_id':request_id,'cumulative_reserved_usd':str(Decimal(held+n)/1000000)})
  if held<40000000<=held+n:self.journal('planned_spend_warning',{'threshold_usd':40,'emergency_shared_cap_usd':50,'action':'continue_genuine_BLE'})
 def settle(self,request_id,known_upper):
  # Only settle after the frozen client validated completed native output and
  # usage. When cache classes are complete/consistent, apply current Standard
  # rates; missing/invalid breakdown retains the all-input-write upper bound.
  value=Decimal(known_upper)
  events=getattr(self.journal,'events',[])
  usage=next((x.get('usage',{})for x in reversed(events)if x.get('event')=='usage'and x.get('client_request_id')==request_id),{})
  event=next((x for x in reversed(events)if x.get('event')=='usage'and x.get('client_request_id')==request_id),{})
  usage={**usage,'actual_service_tier':event.get('actual_service_tier')}
  detail=usage.get('input_tokens_details')or{}
  total=usage.get('input_tokens');out=usage.get('output_tokens');cached=detail.get('cached_tokens');writes=detail.get('cache_write_tokens')
  if all(type(x)is int and x>=0 for x in [total,out,cached,writes])and cached+writes<=total:
   from r1api.responses import _published_standard_estimate
   priced=_published_standard_estimate(usage)
   if priced is not None:
    exact=Decimal(priced)*Decimal(2 if usage.get('actual_service_tier') in ('fast','priority') else 1)
    value=min(value,exact*Decimal('1.10')) # extra10% cushion; unknown write lifetime retains upper bound
  n=micros(value)
  with self.locked()as c:
   row=c.execute('select held,status from requests where id=?',(request_id,)).fetchone()
   if row is None or row[1]!='reserved_or_uncertain'or n<0 or n>row[0]:raise BudgetError('Invalid settlement')
   c.execute('update requests set held=?,status=?where id=?',(n,'completed_usage_upper',request_id))
   c.execute('update meta set held=held-?,inflight=inflight-1',(row[0]-n,))
 def close_uncertain_local_requests(self,request_ids):
  with self.locked()as c:
   for ident in request_ids:
    row=c.execute('select status from requests where id=?',(ident,)).fetchone()
    if row and row[0]=='reserved_or_uncertain':
     c.execute("update requests set status='locally_closed_cost_retained'where id=?",(ident,))
     c.execute('update meta set inflight=inflight-1')
 def begin_forecast(self,ident):
  with self.locked()as c:
   if c.execute('select stopped from meta').fetchone()[0]:raise RuntimeError('Production stopped after repeated failures')
   row=c.execute('select status,p,genuine,full from forecasts where id=?',(ident,)).fetchone()
   if row:
    if row[0]=='finished':c.execute('update meta set cached=cached+1');return row[1]
    raise RuntimeError('Uncertain or active forecast cannot be duplicated')
   c.execute('insert into forecasts values(?,?,NULL,0,0,?)',(ident,'in_progress',time.time()))
  return None
 def finish_forecast(self,ident,p,genuine,full):
  with self.locked()as c:
   c.execute('update forecasts set status=?,p=?,genuine=?,full=?where id=?',('finished',p,int(genuine),int(full),ident))
   if genuine:c.execute('update meta set real=real+1,full=full+?,consecutive_fallback=0',(int(full),))
   else:c.execute('update meta set fallback=fallback+1,consecutive_fallback=consecutive_fallback+1')
   d=self.snapshot(c);total=d['real']+d['fallback']
   stop=d['consecutive_fallback']>=5 or (total>=20 and d['fallback']/total>=.10)
   if stop:c.execute('update meta set stopped=1');d['stopped']=1
  if stop:raise RuntimeError('Production stopped after repeated emergency fallbacks')
  return d
 def snapshot(self,c=None):
  if c is None:
   with self.locked()as db:return self.snapshot(db)
  cols=[r[1]for r in c.execute('pragma table_info(meta)')]
  return dict(zip(cols,c.execute('select * from meta').fetchone()))


def refuse_budget_fallback(events):
 """A resource limit is an explicit failed run, never claimed BLE coverage."""
 if any(x.get('event')=='fallback' and x.get('reason')=='BudgetError' for x in events):
  raise RuntimeError('Production emergency budget/admission limit; no baseline result returned')
