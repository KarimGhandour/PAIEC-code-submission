"""Pinned official source retrieval; explicit opt-in, sizes and hashes checked."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--download',action='store_true');ap.add_argument('--acknowledge-source-terms',action='store_true');ap.add_argument('--family',action='append',default=[]);ap.add_argument('--include-traces',action='store_true');ap.add_argument('--max-bytes',type=int,default=0);ap.add_argument('--destination',type=Path,default=ROOT/'local_data/measurement-db');a=ap.parse_args()
    m=json.loads((ROOT/'artifacts/manifests/measurement_db_inputs.json').read_text());files=[x for x in m['files'] if (not a.family or x['path'].split('/')[0] in a.family) and (a.include_traces or not x['path'].endswith('/traces.parquet'))]
    size=sum(x['size'] for x in files);print(json.dumps({'revision':m['revision'],'selected_files':len(files),'expected_bytes':size,'download':a.download}))
    if not a.download:return
    if not a.acknowledge_source_terms or not 0<size<=a.max_bytes:ap.error('Explicit source-term acknowledgment and sufficient --max-bytes are required')
    from huggingface_hub import hf_hub_download
    for row in files:
        path=Path(hf_hub_download(m['repo'],row['path'],repo_type='dataset',revision=m['revision'],local_dir=str(a.destination)))
        h=hashlib.sha256()
        with path.open('rb') as f:
            for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
        if path.stat().st_size!=row['size'] or (row.get('sha256') and h.hexdigest()!=row['sha256']):raise ValueError('Official file integrity mismatch: '+row['path'])
    print('Pinned source files verified. These are not the frozen derived R1 evidence bundle; see docs/data_provenance.md.')
if __name__=='__main__':main()
