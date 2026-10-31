"""Only the factual acquired-label block differs from frozen R1."""
import copy,math
from r1api.util import sha

def acquisition_ledger(target,labels,keys,budget):
 if budget==0:
  if labels or keys:raise ValueError('Budget zero must be empty')
  return None
 if budget!=7 or len(labels)!=budget or len(keys)!=budget:raise ValueError('Frozen seven-label prefix required')
 groups=[];successes=0
 for (inp,y),key in zip(labels,keys):
  if inp[0]!=target[0] or inp[1]['benchmark_id']!=target[1]['benchmark_id']:raise ValueError('Wrong subject/benchmark acquisition')
  if sha(inp)!=key['input_sha256'] or not key.get('source_group'):raise ValueError('Task-to-outcome pairing mismatch')
  if type(y) not in (int,float) or not math.isfinite(y) or y not in (0,1):raise ValueError('Nonbinary acquisition')
  groups.append(key['source_group']);successes+=int(y)
 return {'acquisition_budget':budget,'observed_responses':len(labels),'successes':successes,'failures':len(labels)-successes,'distinct_original_source_groups':len(set(groups)),'beta_4_4_aggregate_reference':(4+successes)/(8+len(labels))}

def add_ledger(question,ledger):
 if ledger is None:return question
 q=copy.deepcopy(question)
 q['background']+='\n\nCOORDINATOR ACQUISITION LEDGER (deterministic factual counts):\n'+\
  '\n'.join(f'- {k}: {v}' for k,v in ledger.items())+\
  '\nThe Beta(4,4) posterior is an aggregate ability-calibration reference, not the probability for the current question. These counts summarize the same acquired observations already shown above; they are not additional evidence.'
 return q
