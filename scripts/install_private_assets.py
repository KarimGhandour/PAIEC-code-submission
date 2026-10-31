"""Verify an independently authorized local asset bundle before installing it."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('bundle',type=Path);ap.add_argument('--install',action='store_true');a=ap.parse_args()
    m=json.loads((ROOT/'artifacts/manifests/private_assets.json').read_text())['files']
    # Validate all assets before making any change; never accepts an archive or credential.
    for n,info in m.items():
        p=a.bundle/n
        if not p.is_file() or p.is_symlink() or p.stat().st_size!=info['bytes'] or digest(p)!=info['sha256']:raise ValueError('Missing/different authorized asset: '+n)
    if a.install:
        for n in m:
            p=ROOT/'submission'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.bundle/n,p)
    print(json.dumps({'status':'PASS','assets':len(m),'installed':a.install,'credential_handling':False}))
if __name__=='__main__':main()
