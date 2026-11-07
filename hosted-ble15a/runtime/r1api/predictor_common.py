"""Frozen R1 typed-action coordinator, with separately disclosed emergency fallback."""
import json, math, os, tempfile, time, uuid
from pathlib import Path
from agent.belief_state import BeliefState
from agent.tools import SUBMIT_TOOL, dispatch_tool
from agent.prompts import get_system_prompt, format_question_prompt
from comp_pipeline.script.agent_tools import MEASUREMENT_TOOLS
from .question import build_question
from .protocol import decode, parse, wire_schema, SyntaxFailure
from .responses import ResponsesClient, APIError
from .util import sha

HERE=Path(__file__).resolve().parents[1]
TOOLS=[SUBMIT_TOOL,*MEASUREMENT_TOOLS]

def matching_labels(inp,labeled):
    if not isinstance(inp,list) or len(inp)!=2 or not all(isinstance(x,dict) for x in inp):raise ValueError('Expected [subject,item] dictionaries')
    subject,item=inp
    if not isinstance(item.get('item_content'),str):raise ValueError('Missing item text')
    result=[]
    for entry in labeled or []:
        if not isinstance(entry,(list,tuple)) or len(entry)!=2:raise ValueError('Malformed acquired label')
        observed,y=entry
        if not isinstance(observed,(list,tuple)) or len(observed)!=2 or not all(isinstance(x,dict) for x in observed):raise ValueError('Malformed acquired input')
        if observed[0]!=subject:continue
        # Anonymous IDs are used only for equality, never reverse-mapped to a family.
        a=item.get('benchmark_id');b=observed[1].get('benchmark_id')
        if a is not None or b is not None:
            if a!=b:continue
        if type(y) not in (int,float) or not math.isfinite(y) or y not in (0,1):raise ValueError('Nonbinary acquired label')
        if not isinstance(observed[1].get('item_content'),str):raise ValueError('Missing acquired item text')
        result.append([observed,int(y)])
    if len(result)>31:raise ValueError('More than31 matching acquired labels')
    return result

def beta44(labels):return (4+sum(y for _,y in labels))/(8+len(labels))

class Journal:
    def __init__(self,root=None):
        base=Path(root or os.environ.get('PAIEC_AUDIT_DIR') or Path('/tmp')/'paiec-r1-api')
        base.mkdir(parents=True,exist_ok=True)
        self.directory=base/uuid.uuid4().hex;self.directory.mkdir(mode=0o700)
        self.events=[]
    def __call__(self,kind,data):
        event={'event':kind,'time':time.time(),**data};self.events.append(event)
        with (self.directory/'audit.jsonl').open('a') as stream:
            stream.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
        if os.environ.get('PAIEC_PREDICTION_WORKER_ID') is not None:
            print('PAIEC_R1_AUDIT '+json.dumps({'forecast_id':self.directory.name,**event},ensure_ascii=False,allow_nan=False),flush=True)

def live_db(inp,labels):
    from .db import AuditedDB
    excluded=json.loads((HERE/'r1api/excluded_families.json').read_text())
    protected=json.loads((HERE/'data/protected_inputs.json').read_text())
    return AuditedDB(excluded_families=excluded,targets=protected+[{'input':inp}]+[{'input':x} for x,_ in labels],target_subject=inp[0],quality=False,static_cache=True)

