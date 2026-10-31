"""Frozen source-only factor method on separately supplied authorized arrays.

No encoder downloads or inference. Target evaluation labels are opened only after
predictions are saved. Historical arrays/groups are not supplied by this release.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from .model import train_factor,metadata_matrix,new_subject_components,adapt,logit,sigmoid,metrics
from .calibration import calibrate
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--target-features',type=Path,required=True);ap.add_argument('--metadata',type=Path,required=True);ap.add_argument('--acquisitions',type=Path,required=True);ap.add_argument('--evaluation',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise FileExistsError('Use a new output directory; no overwrite/tuning')
    s=np.load(a.source,allow_pickle=False);t=np.load(a.target_features,allow_pickle=False);aq=np.load(a.acquisitions,allow_pickle=False);m=json.loads(a.metadata.read_text())
    if 'y' in t.files:raise ValueError('Target-feature file must contain no outcomes')
    x=s['embeddings_all'].astype(np.float32);si=s['source_indices'];ti=t['target_indices'];groups=t['groups'];ys=s['y'];ai=aq['indices'];ay=aq['y']
    assert x.ndim==2 and x.shape[1]==768 and np.isfinite(x).all()
    np.testing.assert_allclose(np.linalg.norm(x,axis=1),1,atol=1e-5)
    assert not set(si)&set(ti) and ys.shape==(len(si),len(m['source_models']))
    assert set(m['source_models'])==set(m['target_models']) and len(set(m['source_models']))==9
    assert len(ai)==len({groups[i] for i in ai})==7 and ay.shape==(7,len(m['target_models']))
    assert set(np.unique(ys))<={0,1} and set(np.unique(ay))<={0,1}
    sm,vocab=metadata_matrix(m['source_subjects'],m['source_models']);tm,_=metadata_matrix(m['target_subjects'],m['target_models'],vocab)
    _,state,(zall,_,_),info=train_factor(x,sm,[(si,np.arange(len(sm)),ys)],'cpu')
    vectors,bias=new_subject_components(state,tm);z=zall[ti]
    ability=(1+ys.sum(axis=0))/(2+len(ys));by_model={f:float(np.mean(ability[np.array(m['source_models'])==f])) for f in set(m['source_models'])}
    prior=logit(np.array([by_model[f] for f in m['target_models']]));scalar=np.tile(sigmoid(prior),(len(ti),1));baseline,_=calibrate(logit(scalar),ai,ay,prior)
    factor,_=adapt(z,vectors,ai,ay,prior);methods={'source_subject':scalar,'calibrated_subject':baseline,'factor_budget_zero':sigmoid(z@vectors.T+bias),'calibrated_factor':factor}
    a.output.mkdir(parents=True);pred=a.output/'predictions_before_scoring.npz';np.savez_compressed(pred,**methods)
    (a.output/'prediction_freeze.json').write_text(json.dumps({'predictions_sha256':hashlib.sha256(pred.read_bytes()).hexdigest(),'evaluation_opened':False,'training':info},indent=2)+'\n')
    # Only now may the separate target scoring key be read.
    ev=np.load(a.evaluation,allow_pickle=False);ei=ev['indices'];y=ev['y'];assert not {groups[i] for i in ai}&{groups[i] for i in ei}
    assert y.shape==(len(ei),len(m['target_models'])) and set(np.unique(y))<={0,1}
    result={k:metrics(y,p[ei]) for k,p in methods.items()};(a.output/'scores.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
