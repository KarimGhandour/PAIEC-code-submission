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

def forecast(inp,labeled=None,*,config=None,client_factory=ResponsesClient,db_factory=live_db,journal=None):
    labels=matching_labels(inp,labeled)
    cfg=config or json.loads((HERE/'submission_config.json').read_text())
    log=journal or Journal(); db=None;started=time.monotonic();deadline=started+900
    log('forecast_start',{'input_sha256':sha(inp),'acquisition_prefix_sha256':sha(labels),'acquired_labels':len(labels),'procedure':'frozen R1; no deterministic ledger'})
    try:
        # A smoke test is explicitly the emergency path, never a simulated API success.
        if os.environ.get('PREDICTIVE_EVAL_LOCAL_SMOKE_TEST')=='1':raise APIError('Organizer offline smoke: explicit emergency fallback')
        client=client_factory(cfg,log)
        question=build_question(*inp,labeled=labels)
        system=get_system_prompt(5,TOOLS)
        instructions=system+json.loads((HERE/'r1api/transport_note.json').read_text())
        messages=[{'role':'system','content':system},{'role':'user','content':format_question_prompt(question)}]
        state=BeliefState();seen=1
        for step in range(1,6):
            state.step=step;tools=[SUBMIT_TOOL] if step==5 else TOOLS
            delta=messages[seen:]
            if delta and delta[0]['role']=='assistant':delta=delta[1:]
            payload=json.dumps({'available_ble_tools':tools,'new_public_messages':delta,'force_submit':step==5,'semantic_backend':'AUDITED-local-MiniLM'},ensure_ascii=False)
            error=None;repair_tools=tools
            for repair in range(3):
                output=None
                sent=payload if error is None else json.dumps({'schema_repair':{'validation_error':str(error)[:300],
                    'instruction':'Correct the previous action to satisfy the output schema. No new evidence or outcomes are supplied. Return only the corrected action.'}},ensure_ascii=False)
                try:
                    output=parse(client.call(instructions,sent,wire_schema(repair_tools),deadline-time.monotonic()))
                    name,args=decode(output,repair_tools);break
                except SyntaxFailure as exc:
                    log('schema_failure',{'step':step,'repair':repair,'error':str(exc)[:300]})
                    if repair==2:raise APIError('Schema repairs exhausted') from None
                    error=exc
                    if isinstance(locals().get('output'),dict):
                        badname=(output.get('action') or {}).get('tool_name')
                        restricted=[t for t in tools if t['function']['name']==badname]
                        if restricted:repair_tools=restricted
            if time.monotonic()>=deadline:raise APIError('Deadline before dispatch')
            if name!='submit' and db is None:
                try:db=db_factory(inp,labels)
                except Exception as exc:
                    from .responses import _failure
                    info=_failure(exc,client.key);info['stage']='local_firewall_initialization'
                    log('controller_failed',{'step':step,'tool':name,**info})
                    raise
            try:
                evidence,state,metadata=dispatch_tool(name,args,state,db,str(log.directory))
            except Exception as exc:
                from .responses import _failure
                info=_failure(exc,client.key);info['stage']='local_controller'
                log('controller_failed',{'step':step,'tool':name,**info})
                raise
            if time.monotonic()>=deadline:raise APIError('Deadline during tool execution')
            log('scientific_action',{'step':step,'tool':name,'arguments':args,'public_belief':state.to_dict(),
                'evidence':evidence,'evidence_sha256':sha(evidence),'metadata':metadata})
            if name=='submit':
                log('submitted',{'probability':state.p,'actions':step,'requests':client.calls,'seconds':time.monotonic()-started,'fallback':False})
                return state.p
            call_id='typed-'+str(step)
            messages.extend([{'role':'assistant','content':'','tool_calls':[{'id':call_id,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},
                {'role':'tool','tool_call_id':call_id,'content':evidence},
                {'role':'user','content':state.to_prompt_str(5)+'\nConsider the new tool result when updating your next belief.'}])
            seen=len(messages)-3
        raise APIError('No valid final submission')
    except Exception as exc:
        # Preserve failures as failures, with a separately marked deterministic prediction.
        # Error strings can include credentials from injected libraries; log class/code only.
        p=beta44(labels)
        code=type(exc).__name__
        log('fallback',{'probability':p,'fallback':'Beta(4,4)','reason':code,'seconds':time.monotonic()-started})
        return p
    finally:
        if db is not None:db.close()
