"""Write an ignored, disabled-by-default configuration with an EMPTY credential."""
import json,os,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=ROOT/'submission/submission_config.json'
    if p.exists():raise FileExistsError('Configuration already exists; will not overwrite')
    cfg=json.loads((ROOT/'submission/config.example.json').read_text());cfg['run_budget_id']='public_r1_'+uuid.uuid4().hex
    cfg['enable_paid_inference']=False;cfg['api_keys']={'OPENAI_API_KEY':''}
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(cfg,f,indent=2);f.write('\n')
    print('Created ignored owner-only configuration; paid inference disabled; credential empty.')
if __name__=='__main__':main()
