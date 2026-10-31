import importlib,json,math,os,socket,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'submission'),str(ROOT/'submission/src'),str(ROOT/'tests')]
from r1api import db as backend,predictor as p,assets
from r1api.responses import ResponsesClient
from r1api.util import sha
from test_ble_api_parity_001 import Mock,action,SUBJECT,ITEM,INP
from synthetic import make_database
class PublicReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        stop=patch.object(socket.socket,'connect',side_effect=AssertionError('No network permitted'));stop.start();self.addCleanup(stop.stop)
    def test_exact_source_and_prompt_hash(self):
        import hashlib
        manifest=json.loads((ROOT/'artifacts/manifests/selected_source.json').read_text())
        for f in manifest['source_files']:self.assertEqual(hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest(),f['sha256'],f['path'])
        self.assertFalse((ROOT/'submission/labeling.py').exists())
        self.assertEqual(len(p.TOOLS),9)
        prompts=json.loads((ROOT/'artifacts/manifests/prompt_hashes.json').read_text())
        system=p.get_system_prompt(5,p.TOOLS)
        self.assertEqual(sha(system),prompts['r1_system_canonical_json_sha256'])
        self.assertEqual(sha(system+json.loads((ROOT/'submission/r1api/transport_note.json').read_text())),prompts['r1_API_instructions_canonical_json_sha256'])
    def test_synthetic_eight_tools_and_source_exclusion(self):
        path=make_database(self.root)
        query=np.zeros((1,384),dtype=np.float32);query[0,0]=1
        with patch.object(backend,'RUN',self.root),patch.object(backend,'encode',return_value=query):
            db=backend.AuditedDB(excluded_families=['excluded'],targets=[{'input':[SUBJECT,{'item_content':'Invented protected-source variant'}]}],path=path)
            try:
                calls=[('find_model',{'model_name':'Invented'}),('search_benchmarks',{'query':'arithmetic'}),('get_benchmark',{'benchmark_id':'synthetic'}),('get_scores',{'benchmark_id':'synthetic'}),('search_items',{'benchmark_id':'synthetic','query':'code'}),('get_item',{'benchmark_id':'synthetic','item_id':'i1'}),('get_trace',{'benchmark_id':'synthetic','item_id':'i1','model':'Invented'}),('semantic_search_items',{'query':'arithmetic','k':5})]
                packets={n:json.loads(getattr(db,n)(**kw)) for n,kw in calls}
                self.assertEqual(len(packets),8);self.assertEqual(packets['get_scores']['evidence'][0]['trials'],2)
                trace=packets['get_trace']['evidence'][0];self.assertTrue(trace['trace_truncated']);self.assertEqual(len(trace['trace']),4000)
                self.assertEqual(trace['full_trace_sha256'],sha('Synthetic trace '+'x'*4500))
                self.assertEqual(json.loads(db.get_item('synthetic','i3'))['evidence']['status'],'excluded_or_unavailable')
                self.assertEqual(json.loads(db.get_scores('excluded'))['evidence']['status'],'excluded_or_unavailable')
                self.assertFalse(db.c.execute("select 1 from permitted_items where source_key='shared'").fetchone())
                self.assertEqual({r['item_id'] for r in packets['semantic_search_items']['evidence']['results']},{'i1','i2'})
            finally:db.close()
    def test_root_interface_all_six_budgets_with_mock_transport(self):
        # Root import hydration is bypassed only in this synthetic no-data fixture.
        with patch.object(assets,'hydrated_corpus',return_value=self.root/'synthetic.sqlite'):
            model=importlib.import_module('model')
        original=p.forecast
        for n in [0,1,3,7,15,31]:
            mock=Mock([action('find_model',model_name='Invented'),action(prob=.63)])
            class DB:
                def find_model(self,*a,**k):return '{"tool":"find_model","evidence":[{"source":"invented"}]}'
                def close(self):pass
            def configured(inp,labels):return original(inp,labels,config={'max_forecast_usd':.5},journal=p.Journal(self.tmp.name),client_factory=lambda c,j:ResponsesClient(c,j,post=mock),db_factory=lambda *a:DB())
            labels=[[[SUBJECT,{**ITEM,'item_content':'invented '+str(i)}],i%2] for i in range(n)]
            with patch.object(model,'forecast',configured):self.assertEqual(model.predict(INP,labels),.63)
            self.assertEqual(len(mock.requests),2)
            for item in mock.responses[0]['output']:self.assertIn(item,mock.requests[1]['input'])
    def test_missing_assets_fail_closed(self):
        assets.hydrated_corpus.cache_clear()
        try:
            with patch.object(assets,'DATA',self.root),patch.object(assets,'CACHE_ROOT',self.root/'cache'):
                with self.assertRaises(FileNotFoundError):assets.hydrated_corpus()
        finally:assets.hydrated_corpus.cache_clear()
    def test_tampered_static_cache_fails_before_SQL(self):
        bad=self.root/'cache.json';bad.write_text(json.dumps({'format':'paiec-r1-firewall-v1','corpus_sha256':'0'*64}))
        with self.assertRaises(PermissionError):backend._static_firewall(bad,[],[],{},self.root/'never-opened.sqlite')
    def test_original_and_equal_family_estimands_are_distinct(self):
        from analysis.scoring import macro
        from analysis.family_scoring import macro as fm
        rows=[{'family':f,'subject_id':s,'budget':0,'ys':[0],'p':p0} for f,s,p0 in [('a','1',0.),('a','2',0.),('b','3',1.)]]
        self.assertAlmostEqual(macro(rows,'p'),1/3);self.assertAlmostEqual(fm(rows,'p'),.5)
    def test_official_six_budget_ALC(self):
        from analysis.official_alc import brier_alc,BUDGETS
        self.assertAlmostEqual(brier_alc({b:.25 for b in BUDGETS}),.25)
        self.assertAlmostEqual(brier_alc({b:float(b==7) for b in BUDGETS}),.2)
        with self.assertRaises(ValueError):brier_alc({0:.25,7:.25})
    def test_ledger_is_separate_and_pairing_checked(self):
        from experiments.ble_ledger_003.ledger import acquisition_ledger
        labels=[[[SUBJECT,{**ITEM,'item_content':str(i)}],int(i<2)] for i in range(7)];keys=[{'input_sha256':sha(x),'source_group':str(i)} for i,(x,y) in enumerate(labels)]
        ledger=acquisition_ledger(INP,labels,keys,7);self.assertEqual((ledger['successes'],ledger['failures']),(2,5))
        keys[0]['input_sha256']='bad'
        with self.assertRaises(ValueError):acquisition_ledger(INP,labels,keys,7)
    def test_cluster_bootstrap_reproducible(self):
        from analysis.bootstrap import paired_interval
        rows=[{'family':f,'subject_id':'s','source_group':str(i),'budget':b,'ys':[i%2],'a':.5,'c':.6} for f in ['a','b'] for i in range(3) for b in [0,7]]
        self.assertEqual(paired_interval(rows,'a','c',25),paired_interval(rows,'a','c',25))
