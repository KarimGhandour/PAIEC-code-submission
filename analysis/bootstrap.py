import numpy as np
from .scoring import macro

def paired_interval(rows,left,right,draws=2000):
 rng=np.random.default_rng(20261029);families=sorted({r['family'] for r in rows});values=[]
 for _ in range(draws):
  sample=[]
  for draw,fi in enumerate(rng.integers(0,len(families),len(families))):
   f=families[fi];family=[r for r in rows if r['family']==f]
   # These cohorts assign each target group to one subject; preserve each subject stratum.
   for subject in sorted({r['subject_id'] for r in family}):
    rr=[r for r in family if r['subject_id']==subject];groups=sorted({r['source_group'] for r in rr})
    for gi in rng.integers(0,len(groups),len(groups)):
     sample.extend({**r,'family':str(draw)+':'+f} for r in rr if r['source_group']==groups[gi])
  values.append(macro(sample,left)-macro(sample,right))
 return {'gain':macro(rows,left)-macro(rows,right),'family_source_cluster_95':np.quantile(values,[.025,.975]).tolist(),'draws':draws,'independent_families':len(families),'estimand':'Same equal subject/family/budget-cell macro as point score; family then subject-stratified source-group resampling. Budgets/trials remain together.','positive_means_improvement':True}
