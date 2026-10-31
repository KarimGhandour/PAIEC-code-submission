"""Score a user-authorized local row panel; never reads any dataset by default."""
import argparse,json,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.scoring import score
from analysis.family_scoring import macro as family_macro,interval
from analysis.bootstrap import paired_interval
def main():
    ap=argparse.ArgumentParser();ap.add_argument('records',type=Path);ap.add_argument('--left',required=True);ap.add_argument('--right',required=True);ap.add_argument('--estimand',choices=['original_confirmation','equal_family'],required=True);ap.add_argument('--bootstrap-draws',type=int,default=2000);a=ap.parse_args()
    rows=json.loads(a.records.read_text())
    if not rows:raise ValueError('Empty panel')
    for r in rows:
        for k in ['family','subject_id','source_group','target_id','budget','ys',a.left,a.right]:assert k in r,k
        if not r['ys'] or any(type(y) not in [int,float] or y not in [0,1] for y in r['ys']):raise ValueError('Nonbinary or empty outcomes')
        for m in [a.left,a.right]:
            if not math.isfinite(r[m]) or not 0<=r[m]<=1:raise ValueError('Invalid probability')
    if a.estimand=='original_confirmation':result={'scores':{m:score(rows,m) for m in [a.left,a.right]},'paired':paired_interval(rows,a.left,a.right,a.bootstrap_draws)}
    else:result={'scores':{m:{metric:family_macro(rows,m,metric) for metric in ['brier','nll']} for m in [a.left,a.right]},'paired':interval(rows,a.left,a.right,a.bootstrap_draws)}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
