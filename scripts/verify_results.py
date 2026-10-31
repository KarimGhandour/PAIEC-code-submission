"""Recheck published point estimates from released aggregate cells, not hidden labels."""
import json,math,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
def aggregate(path):
    v=json.loads(path.read_text());out={}
    for method in v['methods']:
        out[method]={}
        for metric in ['brier','nll']:
            families=defaultdict(list)
            for c in v['cells']:families[c['family']].append(c['loss_sums'][method][metric]/c['n_trials'])
            values=([sum(x)/len(x) for x in families.values()] if v['aggregation']=='equal_family' else [x for a in families.values() for x in a])
            out[method][metric]=sum(values)/len(values)
    return out
def main():
    root=ROOT/'experiments';result={}
    for name,path in [('confirmation',root/'ble_audited_retrieval_002/confirmation_aggregate_cells.json'),('development',root/'ble_audited_retrieval_002/development_aggregate_cells.json'),('ledger',root/'ble_ledger_003_aggregate_cells.json'),('xhigh',root/'luna_xhigh_004_aggregate_cells.json')]:result[name]=aggregate(path)
    ref=json.loads((root/'ble_audited_retrieval_002/confirmation_reference.json').read_text())['decomposition']['overall']
    for method,key in [('A0','A0_brier'),('R1_initial','initial_brier'),('R1','final_brier')]:assert math.isclose(result['confirmation'][method]['brier'],ref[key],abs_tol=1e-12)
    ledger=json.loads((root/'ble_ledger_003/reference.json').read_text())['by_tier']['Tier1']
    for m in ['A0','R1','R1_LEDGER']:
        for metric in ['brier','nll']:assert math.isclose(result['ledger'][m][metric],ledger['scores'][m][metric],abs_tol=1e-12)
    xhigh=json.loads((root/'luna_xhigh_004/reference.json').read_text())
    for m in ['Medium','Xhigh','Medium_initial','Xhigh_initial']:
        for metric in ['brier','nll']:assert math.isclose(result['xhigh'][m][metric],xhigh['scores'][m][metric],abs_tol=1e-12)
    factor=json.loads((root/'inductive_mf_001/reference.json').read_text());result['factor_transfer']={d:v['incremental_brier_gain'] for d,v in factor['transfer'].items()}
    for d,v in factor['transfer'].items():assert math.isclose(v['scores']['B_calibrated_subject']['brier']-v['scores']['C_calibrated_factor']['brier'],v['incremental_brier_gain'],abs_tol=1e-12)
    print(json.dumps({'status':'PASS','scope':'Aggregate point-estimate arithmetic only. Raw predictions/outcomes and original cluster bootstrap cannot be regenerated from these summaries.','scores':result},indent=2))
if __name__=='__main__':main()
