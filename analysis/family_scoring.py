"""Ledger/xhigh equal-family aggregation, exact archived function bodies."""
import math
from collections import defaultdict
import numpy as np

def macro(rows,method,metric='brier'):
 cells=defaultdict(list)
 for r in rows:
  p=r[method]
  if not math.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid frozen probability')
  for y in r['ys']:
   if y not in (0,1):raise ValueError('Nonbinary outcome')
   cells[(r['family'],r['subject_id'],r['budget'])].append((p-y)**2 if metric=='brier' else -y*math.log(max(p,1e-15))-(1-y)*math.log(max(1-p,1e-15)))
 families=defaultdict(list)
 for (f,s,b),v in cells.items():families[f].append(float(np.mean(v)))
 return float(np.mean([np.mean(v) for v in families.values()]))

def interval(rows,a,b,draws=2000):
 rng=np.random.default_rng(20261029);families=sorted({r['family'] for r in rows});samples=[]
 for _ in range(draws):
  pseudo=[]
  for fi,f in enumerate(rng.choice(families,len(families),replace=True)):
   rr=[r for r in rows if r['family']==f]
   for s in sorted({r['subject_id'] for r in rr}):
    ss=[r for r in rr if r['subject_id']==s];groups=sorted({r['source_group'] for r in ss})
    for gi,g in enumerate(rng.choice(groups,len(groups),replace=True)):
     pseudo.extend({**r,'family':str(fi),'source_group':str(gi)} for r in ss if r['source_group']==g)
  samples.append(macro(pseudo,a)-macro(pseudo,b))
 return {'gain':macro(rows,a)-macro(rows,b),'family_source_group_95':np.quantile(samples,[.025,.975]).tolist(),'draws':draws}
