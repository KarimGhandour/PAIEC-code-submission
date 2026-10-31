import importlib.util,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'scripts/scan_release.py'
spec=importlib.util.spec_from_file_location('release_scanner',path);scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
class ScannerTests(unittest.TestCase):
    def test_credential_detector(self):
        # Construct an invented scanner specimen; no complete key is stored in source.
        value=('sk-'+'proj-'+'A'*45).encode()
        self.assertIn('OpenAI project credential',scan.findings('example.txt',value))
    def test_private_artifact_block(self):
        self.assertIn('prohibited file type/name',scan.findings('private.zip',b'not an archive'))
    def test_empty_configuration(self):
        self.assertEqual(scan.findings('config.example.json',b'{"api_keys":{"OPENAI_API_KEY":""}}'),[])
    def test_protected_records(self):
        self.assertIn('prohibited raw research/session field',scan.findings('record.json',b'{"ys":[0,1]}'))
