"""Deterministic release gate over actual files, index, and every reachable Git blob.

Reports paths/rule names only, never the matched secret. This supplements manual
review; it is not a claim that heuristic scanning proves absence of every secret.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RULES={
 'OpenAI project credential':rb'sk-proj-[A-Za-z0-9_-]{20,}',
 'OpenAI legacy credential':rb'sk-[A-Za-z0-9_-]{40,}',
 'GitHub credential':rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})',
 'HF credential':rb'hf_[A-Za-z0-9]{25,}',
 'PEM private key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'Literal authorization header':rb'(?i)Bearer\s+[A-Za-z0-9_-]{32,}',
 'Signed cloud URL':rb'(?i)(?:X-Amz-Signature|X-Goog-Signature|SharedAccessSignature|sig)=[0-9A-Fa-f]{32,}',
 'Personal workstation path':rb'/(?:Users|home)/[A-Za-z0-9_.-]+/',
 'Sensitive account metadata':rb'"(?:accountId|rateLimitResetCredits|access_token|refresh_token)"\s*:',
}
PROHIBITED={'.zip','.bin','.sqlite','.sqlite3','.parquet','.npy','.npz','.pt','.safetensors','.pkl','.pickle','.ipynb','.jsonl','.gz','.whl'}
def findings(name,raw):
    bad=[];p=Path(name)
    if p.suffix in PROHIBITED or p.name in ['submission_config.json','.env','.env.local'] or p.name.startswith('.env.'):bad.append('prohibited file type/name')
    if len(raw)>2_000_000:bad.append('file exceeds 2 MB release limit')
    if b'\x00' in raw:bad.append('binary content')
    for kind,rule in RULES.items():
        if re.search(rule,raw):bad.append(kind)
    if p.suffix=='.json':
        try:
            value=json.loads(raw)
            def walk(v):
                if isinstance(v,dict):
                    for k,x in v.items():
                        if k=='OPENAI_API_KEY' and x not in ['',None]:bad.append('nonempty JSON API credential')
                        if k in ['ys','evaluation_outcomes','confirmation_outcomes','session_id','native_record_hashes','encrypted_content']:bad.append('prohibited raw research/session field')
                        walk(x)
                elif isinstance(v,list):
                    for x in v:walk(x)
            walk(value)
        except (ValueError,UnicodeError):bad.append('invalid JSON artifact')
    return sorted(set(bad))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--git',action='store_true');a=ap.parse_args();rows=[];errors=[]
    skip={'.git','__pycache__','.venv','build','dist','outputs','local_data','private_assets','private_records'}
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if any(x in skip or x.endswith('.egg-info') or x.startswith('.venv') for x in rel.parts):continue
        if p.is_symlink():errors.append({'path':str(rel),'rules':['symlink forbidden']});continue
        if not p.is_file():continue
        raw=p.read_bytes();bad=findings(str(rel),raw)
        rows.append({'path':str(rel),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        if bad:errors.append({'path':str(rel),'rules':bad})
    blobs=0;index_files=0
    if a.git:
        staged=git('ls-files','-s','-z').split(b'\0')
        for entry in staged:
            if not entry:continue
            meta,name=entry.split(b'\t',1);mode,oid,stage=meta.split();raw=git('cat-file','blob',oid.decode());index_files+=1
            bad=findings(name.decode(),raw)
            if mode not in [b'100644',b'100755']:bad.append('unexpected Git mode')
            if bad:errors.append({'path':name.decode(),'scope':'git-index','rules':bad})
        refs=subprocess.run(['git','rev-parse','--verify','HEAD'],cwd=ROOT,capture_output=True)
        if refs.returncode==0:
            for line in git('rev-list','--objects','--all').splitlines():
                pair=line.split(b' ',1);oid=pair[0].decode()
                if git('cat-file','-t',oid).strip()!=b'blob':continue
                raw=git('cat-file','blob',oid);name=pair[1].decode() if len(pair)>1 else 'git-object';bad=findings(name,raw);blobs+=1
                if bad:errors.append({'path':name,'scope':'git-history','rules':bad})
    report={'status':'PASS' if not errors else 'BLOCKED','files':len(rows),'source_bytes':sum(x['bytes'] for x in rows),'git_index_files':index_files,'git_history_blobs':blobs,'findings':errors,'rule_count':len(RULES),'limits':'Heuristic/structural checks plus manual whitelist review; not a mathematical guarantee against arbitrary secrets.'}
    print(json.dumps(report,indent=2));raise SystemExit(0 if not errors else 1)
if __name__=='__main__':main()
