"""Validate every whitelisted inference file against its approved compact-ZIP hash."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    manifest=json.loads((ROOT/'artifacts/manifests/selected_source.json').read_text())
    for f in manifest['source_files']:
        raw=(ROOT/f['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==f['sha256'],f['path']
        assert len(raw)==f['bytes'],f['path']
    return {'status':'PASS','exact_files':len(manifest['source_files']),'approved_compact_sha256':manifest['compact_sha256']}
if __name__=='__main__':print(json.dumps(check(),indent=2))
