"""Deployment-only adapter: bounded three-action intermediate-readout rescue; scientific variant."""
import hashlib,json,math,os,ssl,time
from decimal import Decimal
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'src')]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
from r1api import responses,run_budget
from r1api.predictor import forecast,matching_labels,beta44
from r1api.util import sha
from production_budget import ProductionBudget,private_root,refuse_budget_fallback
from telemetry import SanitizedJournal,instrument_dispatch,sanitized_details
# Default 30m cache writes cost1.25x Standard input. Charge ALL input at that
# rate for reserve/settlement; no cache discounts are assumed by this guard.
# Body/input/schema/encrypted continuation stay unchanged. Length bound in frozen
# client keeps the request below the272K long-context threshold.
responses.INPUT_CEILING_PER_M=Decimal('.25')
responses.OUTPUT_CEILING_PER_M=Decimal('.50')
responses.REGIONAL_CEILING=Decimal('1')
responses.MAX_REQUESTS=4
run_budget.RunBudget=ProductionBudget
CFG=json.loads((HERE/'submission_config.json').read_text())
_READY=False

def initialize():
 global _READY
 if _READY:return
 ca=HERE/'cacert.pem'
 if hashlib.sha256(ca.read_bytes()).hexdigest()!='2ef52ad56b4803e264045c915e55c236cbfa045b84b81efefc218a19eb44bd2b':raise RuntimeError('CA integrity')
 c=ssl.create_default_context(cafile=str(ca))
 if not c.check_hostname or c.verify_mode!=ssl.CERT_REQUIRED or c.cert_store_stats()['x509_ca']<118:raise RuntimeError('TLS verification')
 os.environ['SSL_CERT_FILE']=str(ca);os.environ['REQUESTS_CA_BUNDLE']=str(ca)
 from r1api import assets
 assets.CACHE_ROOT=private_root(CFG)/'assets'
 assets.hydrated_corpus()
 _READY=True

def predict(input:list[dict],labeled:list=None)->float:
 labels=matching_labels(input,labeled)
 # These are narrowly scoped official offline validation paths. Runtime flags
 # are read on every call, with no latched import-time exemption.
 eligible=isinstance(input[1].get('benchmark_id'),str)and bool(input[1]['benchmark_id'])
 if os.environ.get('PREDICTIVE_EVAL_LOCAL_SMOKE_TEST')=='1'or not eligible:return beta44(labels)
 started=time.monotonic();initialize();root=private_root(CFG)
 log=SanitizedJournal(root/'journals');budget=ProductionBudget(CFG,log)
 ident=sha({'input':input,'labeled':labels})
 cached=budget.begin_forecast(ident)
 if cached is not None:return float(cached)
 class Client(responses.ResponsesClient):
  def _post(self,body,timeout,client_request_id):
   from aims_r1_transport import post_r1
   if 'prompt_cache_options'in body or 'prompt_cache_retention'in body:raise responses.APIError('Unexpected cache configuration',stage='preflight')
   return post_r1(self.key,body,timeout,client_request_id,log)
 with instrument_dispatch(log):p=forecast(input,labels,config=CFG,client_factory=Client,journal=log)
 refuse_budget_fallback(log.events)
 native_submit=any(x['event']=='submitted'and x.get('fallback')is False for x in log.events)
 genuine=native_submit or any(x['event']=='intermediate_return'for x in log.events)
 actions=[x for x in log.events if x['event']=='scientific_action']
 received=[x for x in log.events if x['event']=='response_received']
 valid_beliefs=[x for x in log.events if x['event']=='belief_validated']
 full=genuine and any(x['tool']!='submit'for x in actions)and len(valid_beliefs)>=2
 request_ids=[x['client_request_id']for x in log.events if x['event']=='request_started']
 budget.close_uncertain_local_requests(request_ids)
 if not math.isfinite(p)or not 0<=p<=1:raise RuntimeError('Invalid final prediction')
 totals=budget.finish_forecast(ident,p,genuine,full)
 print('PAIEC_PRODUCTION_SUMMARY '+json.dumps({'forecast_id':ident,'budget':len(labels),'genuine_submit':native_submit,'genuine_model_probability':genuine,'variant':'completion001','full_retrieval_continuation':full,'probability':p,'seconds':time.monotonic()-started,'requests':sum(x['event']=='request_started'for x in log.events),'responses':len(received),'counts':totals,**sanitized_details(log.events)},allow_nan=False),flush=True)
 return float(p)
