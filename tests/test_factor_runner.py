"""Numerical runner smoke on invented arrays, never historical model training."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
class FactorRunnerTest(unittest.TestCase):
    def test_source_only_runner_with_separate_scoring_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);rng=np.random.default_rng(7);x=rng.normal(size=(20,768)).astype(np.float32);x/=np.linalg.norm(x,axis=1)[:,None]
            np.savez(p/'source.npz',embeddings_all=x,source_indices=np.arange(10),y=rng.integers(0,2,size=(10,9)))
            np.savez(p/'target.npz',target_indices=np.arange(10,20),groups=np.array(['g'+str(i) for i in range(10)]))
            np.savez(p/'acquired.npz',indices=np.arange(7),y=rng.integers(0,2,size=(7,9)))
            np.savez(p/'evaluation.npz',indices=np.arange(7,10),y=rng.integers(0,2,size=(3,9)))
            m={'source_models':['invented/'+str(i) for i in range(9)],'target_models':['invented/'+str(i) for i in range(9)],'source_subjects':[{'provider':'invented','harness':'source'} for i in range(9)],'target_subjects':[{'provider':'invented','harness':'target'} for i in range(9)]};(p/'metadata.json').write_text(json.dumps(m))
            result=subprocess.run([sys.executable,'-m','experiments.inductive_mf_001.run_transfer','--source',str(p/'source.npz'),'--target-features',str(p/'target.npz'),'--metadata',str(p/'metadata.json'),'--acquisitions',str(p/'acquired.npz'),'--evaluation',str(p/'evaluation.npz'),'--output',str(p/'output')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[-1000:]);freeze=json.loads((p/'output/prediction_freeze.json').read_text());self.assertFalse(freeze['evaluation_opened'])
            pred=np.load(p/'output/predictions_before_scoring.npz');self.assertEqual(pred['calibrated_factor'].shape,(10,9));self.assertTrue(np.isfinite(pred['calibrated_factor']).all())
