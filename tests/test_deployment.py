import json,os,sys,tempfile,unittest,uuid
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'submission'
sys.path[:0]=[str(P),str(P/'src')]

def reserve_worker(args):
    from r1api.run_budget import RunBudget
    from r1api.responses import BudgetError
    root,ident=args
    b=RunBudget({'max_run_usd':1,'run_budget_id':ident,'run_budget_root':root},lambda *a:None)
    try:b.reserve(uuid.uuid4().hex,Decimal('.2'));return True
    except BudgetError:return False

class DeploymentTests(unittest.TestCase):

    def test_corrupt_compact_assets_fail_closed(self):
        from r1api import assets
        from r1api.util import file_sha
        from unittest.mock import patch
        import lzma
        manifest = json.loads((P / 'data/compact_assets.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data = base / 'data'
            data.mkdir()
            cache = base / 'cache'
            with patch.object(assets, 'DATA', data), patch.object(assets, 'CACHE_ROOT', cache):
                try:
                    bad = {**manifest, 'format': 'unknown'}
                    (data / 'compact_assets.json').write_text(json.dumps(bad))
                    assets.hydrated_corpus.cache_clear()
                    with self.assertRaises(PermissionError):
                        assets.hydrated_corpus()
                    packed = data / 'evidence.xz.bin'
                    packed.write_bytes(lzma.compress(b'not a database'))
                    bad = {**manifest, 'packed': 'evidence.xz.bin', 'codec': 'xz', 'packed_sha256': '0' * 64}
                    (data / 'compact_assets.json').write_text(json.dumps(bad))
                    assets.hydrated_corpus.cache_clear()
                    with self.assertRaises(PermissionError):
                        assets.hydrated_corpus()
                    bad['packed_sha256'] = file_sha(packed)
                    (data / 'compact_assets.json').write_text(json.dumps(bad))
                    assets.hydrated_corpus.cache_clear()
                    with self.assertRaises(PermissionError):
                        assets.hydrated_corpus()
                    self.assertFalse(list(cache.rglob('corpus.sqlite')))
                    self.assertFalse(list(cache.rglob('decode-*')))
                finally:
                    assets.hydrated_corpus.cache_clear()

    def test_parallel_spending_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            with ProcessPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(reserve_worker, [(tmp, 'offline_parallel_002')] * 16))
            self.assertEqual(sum(results), 5)
            state = json.loads((Path(tmp) / 'offline_parallel_002/state.json').read_text())
            self.assertEqual(sum((Decimal(x['held_usd']) for x in state['requests'].values())), Decimal(1))

    def test_unknown_reserve_and_cap_mismatch(self):
        from r1api.run_budget import RunBudget
        from r1api.responses import BudgetError
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {'max_run_usd': 1, 'run_budget_id': 'offline_unknown_002', 'run_budget_root': tmp}
            b = RunBudget(cfg, lambda *a: None)
            b.reserve('unknown', Decimal('.6'))
            b.reserve('complete', Decimal('.4'))
            b.settle('complete', Decimal('.02'))
            with self.assertRaises(BudgetError):
                b.reserve('next', Decimal('.4'))
            with self.assertRaises(BudgetError):
                RunBudget({**cfg, 'max_run_usd': 2}, lambda *a: None).reserve('mismatch', Decimal('.1'))

    def test_hosted_journal_survives_checkpoint_and_is_public_only(self):
        import contextlib, io
        from unittest.mock import patch
        from r1api.predictor import Journal
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'TMPDIR': tmp, 'PAIEC_PREDICTION_WORKER_ID': '0'}, clear=False), contextlib.redirect_stdout(output):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('PAIEC_AUDIT_DIR', None)
                log = Journal()
                log('submitted', {'probability': 0.64, 'fallback': False})
                self.assertFalse(str(log.directory).startswith(tmp))
        self.assertTrue((log.directory / 'audit.jsonl').exists())
        self.assertIn('PAIEC_R1_AUDIT', output.getvalue())
        self.assertNotIn('encrypted_content', output.getvalue())
