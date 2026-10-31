"""Offline tests: sockets denied, real archived action/packet replay, no inference."""
import copy, inspect, json, os, socket, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'submission'
sys.path[:0]=[str(P),str(P/'src')]
from r1api import predictor as p
from r1api.responses import ResponsesClient,APIError,credential
from r1api.protocol import decode,SyntaxFailure,wire_schema
from r1api.db import AuditedDB
from r1api.util import file_sha

SUBJECT={'normalized_name':'test-model','provider':'test','harness':'test-harness'}
ITEM={'item_content':'Compute2+2.','benchmark_id':'anonymous-pair'}
INP=[SUBJECT,ITEM]

def action(name='submit',prob=.63,**extra):
    belief={'p':prob,'confidence':'low','update_reasoning':'Offline typed fixture.'}
    args={'updated_belief':belief,**extra}
    if name=='submit':args.update(probability=prob,reasoning='Offline fixture, not an inference result.')
    definition=next(t['function']['parameters'] for t in p.TOOLS if t['function']['name']==name)
    def fill(v,s):
        if s.get('type')=='object':return {k:fill(v[k],child) if k in v else None for k,child in s['properties'].items()}
        if s.get('type')=='array':return [fill(x,s['items']) for x in v]
        return v
    return {'action':{'tool_name':name,'arguments':fill(args,definition)}}

class Mock:
    def __init__(self,actions):self.actions=list(actions);self.requests=[];self.responses=[]
    def __call__(self,body,timeout):
        self.requests.append(copy.deepcopy(body));n=len(self.requests)
        item=self.actions.pop(0)
        if isinstance(item,Exception):raise item
        text=item if isinstance(item,str) else json.dumps(item)
        result={'id':f'resp{n}','status':'completed','model':'gpt-6-luna','reasoning':{'mode':'standard','effort':'medium','context':'current_turn'},
            'output':[{'type':'reasoning','id':f'rs{n}','encrypted_content':f'opaque{n}'},
                {'type':'message','id':f'msg{n}','role':'assistant','status':'completed','content':[{'type':'output_text','text':text}]}],
            'usage':{'input_tokens':1000,'output_tokens':400,'output_tokens_details':{'reasoning_tokens':100}}}
        self.responses.append(copy.deepcopy(result));return result

class ReplayDB:
    def __init__(self,fixture):self.log=[v for v in fixture['tool_log'] if v['tool']!='submit'];self.i=0;self.closed=False
    def close(self):self.closed=True
    def __getattr__(self,name):
        def run(*args,**kwargs):
            record=self.log[self.i];self.i+=1
            assert name==record['tool']
            bound=inspect.signature(getattr(AuditedDB,name)).bind(None,*args,**kwargs).arguments
            for key,value in record['args'].items():assert bound[key]==value,(key,bound,value)
            return record['result']
        return run

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.no_network=patch.object(socket.socket,'connect',side_effect=AssertionError('Network forbidden in offline tests'))
        self.no_network.start();self.addCleanup(self.no_network.stop)
        self.smoke=patch.dict(os.environ,{'PREDICTIVE_EVAL_LOCAL_SMOKE_TEST':'0'})
        self.smoke.start();self.addCleanup(self.smoke.stop)
    def run_case(self,actions,labels=None,inp=INP,db=None,cap=.5):
        self.mock=Mock(actions);self.log=p.Journal(self.tmp.name)
        result=p.forecast(inp,labels,config={'max_forecast_usd':cap},journal=self.log,
            client_factory=lambda c,j:ResponsesClient(c,j,post=self.mock),db_factory=lambda *a:db)
        return result
    def test_six_budgets(self):
        for n in [0,1,3,7,15,31]:
            labels=[[[SUBJECT,{**ITEM,'item_content':str(i)}],i%2] for i in range(n)]
            self.assertEqual(self.run_case([action()],labels),.63)
            body=self.mock.requests[0]
            self.assertEqual(body['reasoning'],{'mode':'standard','effort':'medium'})
            self.assertEqual(body['model'],'gpt-6-luna');self.assertEqual(body['tools'],[])
            self.assertEqual(body['text']['format']['type'],'json_schema')
            self.assertFalse(body['store']);self.assertNotIn('previous_response_id',body)
    @unittest.skip('Private data/native records not redistributed; see docs/reproducibility.md')
    def test_archived_replay(self):
        fixtures=json.loads((ROOT/'runs/BLE-API-PARITY-001/replay_fixtures.json').read_text())
        cohort={t['id']:t for t in json.loads((ROOT/'runs/BLE-LEDGER-003/cohort.json').read_text())}
        acq=json.loads((ROOT/'runs/BLE-LEDGER-003/acquisitions.json').read_text())
        for fixture in fixtures:
            target=cohort[fixture['job']['target_id']];labels=acq[target['acquisition_key']][:fixture['job']['budget']]
            actions=[]
            for a in fixture['valid_actions']:
                args=copy.deepcopy(a['arguments']);belief=args.pop('updated_belief');prob=args.pop('probability',belief['p']);args.pop('reasoning',None)
                wire=action(a['tool'],prob,**args)
                # Preserve the complete archived public belief and final rationale.
                props=next(t['function']['parameters']['properties']['updated_belief']['properties'] for t in p.TOOLS if t['function']['name']==a['tool'])
                wire['action']['arguments']['updated_belief']={k:belief.get(k) for k in props}
                if a['tool']=='submit':wire['action']['arguments']['reasoning']=a['arguments']['reasoning']
                actions.append(wire)
            db=ReplayDB(fixture)
            self.assertEqual(self.run_case(actions,labels,target['input'],db),fixture['forecast'])
            self.assertEqual(db.i,len(fixture['tool_log'])-1);self.assertTrue(db.closed)
            self.assertEqual(self.mock.requests[0]['instructions'].split('\n\nRESPONSES BLE TRANSPORT')[0],fixture['scientific_system_prompt'])
            first=json.loads(self.mock.requests[0]['input'][0]['content'])
            self.assertEqual(first['new_public_messages'][0]['content'],fixture['question_prompt'])
            for i,body in enumerate(self.mock.requests[1:],1):
                for item in self.mock.responses[i-1]['output']:self.assertIn(item,body['input'])
                payload=json.loads(body['input'][-1]['content'])
                self.assertEqual(payload['new_public_messages'][0]['content'],fixture['tool_log'][i-1]['result'])
    def test_five_actions_forces_submission(self):
        class DB:
            def find_model(self,*args,**kwargs):return '{"evidence":[]}'
            def close(self):pass
        self.assertEqual(self.run_case([action('find_model',model_name='test')]*4+[action()],db=DB()),.63)
        last=self.mock.requests[-1]['text']['format']['schema']
        self.assertEqual(last['properties']['action']['anyOf'][0]['properties']['tool_name']['enum'],['submit'])
        self.assertEqual(len(self.mock.requests),5)
    def test_schema_recovery(self):
        self.assertEqual(self.run_case(['bad-json',action()]),.63)
        self.assertEqual(len(self.mock.requests),2)
        self.assertIn('schema_repair',json.loads(self.mock.requests[-1]['input'][-1]['content']))
    def test_schema_exhaustion_fallback(self):
        self.assertEqual(self.run_case(['bad']*3),.5);self.assertEqual(len(self.mock.requests),3)
        self.assertEqual(self.log.events[-1]['event'],'fallback')
    def test_out_of_range(self):
        self.assertEqual(self.run_case([action(prob=2)]*3),.5)
    def test_official_probability_clipping(self):
        self.assertEqual(self.run_case([action(prob=0)]),.02)
        self.assertEqual(self.run_case([action(prob=1)]),.98)
    def test_submit_probability_authoritative(self):
        value=action(prob=.71);value['action']['arguments']['updated_belief']['p']=.41
        self.assertEqual(self.run_case([value]),.71)
    def test_no_sealed_outcome_reads(self):
        original=Path.open
        def guarded(path,*args,**kwargs):
            if 'sealed' in path.parts or path.name=='outcomes.json':raise AssertionError('Target outcome access forbidden')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):self.assertEqual(self.run_case([action()]),.63)
    def test_unknown_tool(self):
        x=action();x['action']['tool_name']='shell'
        self.assertEqual(self.run_case([x]*3),.5)
    def test_null_defaults(self):
        name,args=decode(action('semantic_search_items',query='code'),p.TOOLS)
        self.assertNotIn('k',args);self.assertNotIn('base_rate_anchor',args['updated_belief'])
    def test_bad_semantic_k(self):
        with self.assertRaises(SyntaxFailure):decode(action('semantic_search_items',query='x',k=100),p.TOOLS)
    def test_label_matching(self):
        labels=[[[SUBJECT,{**ITEM,'item_content':'other'}],1],[[{**SUBJECT,'harness':'different'},ITEM],0],[[SUBJECT,{**ITEM,'benchmark_id':'different'}],0]]
        self.assertEqual(len(p.matching_labels(INP,labels)),1)
        self.assertEqual(p.beta44(p.matching_labels(INP,labels)),5/9)
    def test_same_content_is_not_target_label_lookup(self):
        # An explicit acquired outcome is legitimate; predictor has no target-label lookup.
        self.assertEqual(self.run_case([action()],[[INP,1]]),.63)
    def test_nonbinary_rejected(self):
        with self.assertRaises(ValueError):p.matching_labels(INP,[[INP,.5]])
    def test_invalid_input(self):
        with self.assertRaises(ValueError):p.matching_labels([SUBJECT],[])
    def test_timeout_no_retry(self):
        self.assertEqual(self.run_case([TimeoutError('credential must never be logged')]),.5)
        self.assertEqual(len(self.mock.requests),1)
        self.assertNotIn('credential must',(self.log.directory/'audit.jsonl').read_text())
    def test_spending_cap_no_post(self):
        self.assertEqual(self.run_case([action()],cap=0),.5);self.assertFalse(self.mock.requests)
    def test_credential_source(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(APIError):credential({})
            self.assertEqual(credential({'api_keys':{'OPENAI_API_KEY':'test-private'}}),'test-private')
    def test_disabled_live_transport(self):
        with self.assertRaises(APIError):ResponsesClient({'enable_paid_inference':False},lambda *a:None)
    def test_fresh_state(self):
        self.run_case([action()]);first=self.mock.requests[0]
        self.run_case([action()]);second=self.mock.requests[0]
        self.assertEqual(len(first['input']),1);self.assertEqual(len(second['input']),1)
    def test_native_output_rejected(self):
        log=p.Journal(self.tmp.name)
        def malicious(body,timeout):
            r=Mock([action()])(body,timeout);r['output'].insert(0,{'type':'function_call','name':'shell'});return r
        client=ResponsesClient({'max_forecast_usd':.5},log,post=malicious)
        with self.assertRaises(APIError):client.call('x','y',wire_schema(p.TOOLS),10)
    def test_wrong_model_rejected(self):
        def wrong(body,timeout):
            r=Mock([action()])(body,timeout);r['model']='other';return r
        client=ResponsesClient({'max_forecast_usd':.5},lambda *a:None,post=wrong)
        with self.assertRaises(APIError):client.call('x','y',wire_schema(p.TOOLS),10)
    @unittest.skip('Private data/native records not redistributed; see docs/reproducibility.md')
    def test_real_sql_filters_and_packet_parity(self):
        fixture=json.loads((ROOT/'runs/BLE-API-PARITY-001/replay_fixtures.json').read_text())[0]
        cohort={t['id']:t for t in json.loads((ROOT/'runs/BLE-LEDGER-003/cohort.json').read_text())}
        target=cohort[fixture['job']['target_id']]
        db=p.live_db(target['input'],[])
        try:
            for family in ['engdesign','bertaqa','researchcodebench']:
                self.assertIn('excluded_or_unavailable',db.get_scores(family))
            expected=next(t['result'] for t in fixture['tool_log'] if t['tool']=='get_scores')
            self.assertEqual(db.get_scores('algotune','OpenAI o4-mini'),expected)
            self.assertIsNone(db.c.execute('select * from permitted_items where content_hash=?',(__import__('r1api.util',fromlist=['content_hash']).content_hash(target['input'][1]['item_content']),)).fetchone())
        finally:db.close()

if __name__=='__main__':unittest.main(verbosity=2)
