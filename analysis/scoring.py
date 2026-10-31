"""Historical estimands; not interchangeable with six-budget ALC."""
import math
from collections import defaultdict
import numpy as np

def loss(y,p,kind):
 return float(np.mean((np.asarray(y)-p)**2 if kind=='brier' else -np.asarray(y)*np.log(p)-(1-np.asarray(y))*np.log1p(-p)))

def macro(rows,m,kind='brier'):
 groups=defaultdict(lambda:np.zeros(2))
 for r in rows:groups[(r['family'],r['subject_id'],r['budget'])]+=np.array([loss(r['ys'],r[m],kind)*len(r['ys']),len(r['ys'])])
 return float(np.mean([v[0]/v[1] for v in groups.values()]))

def score(rows,m):
 out={'brier':macro(rows,m),'nll':macro(rows,m,'nll'),'family':{},'budget':{},'subject':{}}
 for name,field in [('family','family'),('budget','budget'),('subject','subject_id')]:
  for v in sorted({r[field] for r in rows}):
   rr=[r for r in rows if r[field]==v];out[name][str(v)]={'brier':macro(rr,m),'nll':macro(rr,m,'nll'),'questions':len({r['target_id'] for r in rr})}
 return out
