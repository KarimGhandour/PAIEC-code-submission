"""Completion-first R1 scientific variant, never represented as full five-action BLE.

The original five-action model-visible prefix, Medium reasoning, legal labels,
tools, masks and native encrypted continuation are unchanged. The controller
can return a validated intermediate belief instead of asking for a final action.
"""
import json, math, os, signal, threading, time
from contextlib import contextmanager
from pathlib import Path
from agent.belief_state import BeliefState
from agent.tools import SUBMIT_TOOL, dispatch_tool, parse_belief_update
from agent.prompts import get_system_prompt, format_question_prompt
from comp_pipeline.script.agent_tools import MEASUREMENT_TOOLS
from .question import build_question
from .protocol import decode, parse, wire_schema, SyntaxFailure
from .responses import ResponsesClient, APIError, BudgetError
from .util import sha
from .predictor_common import matching_labels, beta44, Journal, live_db

HERE=Path(__file__).resolve().parents[1]
TOOLS=[SUBMIT_TOOL,*MEASUREMENT_TOOLS]
POLICY=json.loads((HERE/'rescue_policy.json').read_text())
class InferenceDeadline(BaseException):pass

@contextmanager
def deadline_guard(deadline):
    # The official worker calls predict in its main thread. Never overwrite an
    # already armed organizer timer; its earlier failure remains authoritative.
    owned=(threading.current_thread()is threading.main_thread() and hasattr(signal,'setitimer')
           and signal.getitimer(signal.ITIMER_REAL)==(0.,0.))
    previous=None
    if owned:
        previous=signal.getsignal(signal.SIGALRM)
        def expired(*a):raise InferenceDeadline()
        signal.signal(signal.SIGALRM,expired)
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    try:yield owned
    finally:
        if owned:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def forecast(inp,labeled=None,*,config=None,client_factory=ResponsesClient,db_factory=live_db,journal=None):
    labels=matching_labels(inp,labeled)
    cfg=config or json.loads((HERE/'submission_config.json').read_text())
    log=journal or Journal();db=None;client=None
    started=time.monotonic();deadline=started+POLICY['inference_deadline_seconds']
    latest=None;latest_step=0;repairs=0;completed_retrievals=0
    log('forecast_start',{'input_sha256':sha(inp),'acquisition_prefix_sha256':sha(labels),'acquired_labels':len(labels)})
    def finish(reason):
        if latest is not None:
            log('intermediate_return',{'probability':latest,'step':latest_step,'reason':reason,
                'requests':client.calls if client else 0,'seconds':time.monotonic()-started,'fallback':False})
            return float(latest)
        p=beta44(labels)
        log('fallback',{'probability':p,'reason':reason,'fallback':'Beta(4,4)','seconds':time.monotonic()-started})
        return float(p)
    try:
        with deadline_guard(deadline)as timer_owned:
            log('inference_deadline',{'seconds':POLICY['inference_deadline_seconds'],'category':'POSIX_TIMER'if timer_owned else'COOPERATIVE_EXISTING_TIMER_OR_THREAD'})
            if os.environ.get('PREDICTIVE_EVAL_LOCAL_SMOKE_TEST')=='1':return finish('Official_offline_smoke')
            client=client_factory(cfg,log)
            question=build_question(*inp,labeled=labels)
            system=get_system_prompt(5,TOOLS)
            instructions=system+json.loads((HERE/'r1api/transport_note.json').read_text())
            messages=[{'role':'system','content':system},{'role':'user','content':format_question_prompt(question)}]
            state=BeliefState();seen=1
            for step in range(1,POLICY['maximum_valid_actions']+1):
                remaining=deadline-time.monotonic()
                if remaining<=POLICY['finalization_margin_seconds']:return finish('Between_call_deadline')
                if step==3 and remaining<POLICY['third_call_minimum_remaining_seconds']:return finish('Third_call_not_admitted')
                state.step=step;tools=TOOLS
                delta=messages[seen:]
                if delta and delta[0]['role']=='assistant':delta=delta[1:]
                payload=json.dumps({'available_ble_tools':tools,'new_public_messages':delta,'force_submit':False,'semantic_backend':'AUDITED-local-MiniLM'},ensure_ascii=False)
                error=None;repair_tools=tools
                while True:
                    remaining=deadline-time.monotonic()-POLICY['finalization_margin_seconds']
                    if remaining<=0:return finish('Before_request_deadline')
                    sent=payload if error is None else json.dumps({'schema_repair':{'validation_error':str(error)[:300],
                        'instruction':'Correct the previous action to satisfy the output schema. No new evidence or outcomes are supplied. Return only the corrected action.'}},ensure_ascii=False)
                    try:
                        returned=client.call(instructions,sent,wire_schema(repair_tools),min(POLICY['maximum_HTTP_call_seconds'],remaining))
                        if time.monotonic()>=deadline:return finish('Late_response')
                        output=parse(returned)
                        name,args=decode(output,repair_tools);break
                    except SyntaxFailure as exc:
                        log('schema_failure',{'step':step,'repair':repairs,'reason':'SyntaxFailure'})
                        if repairs>=POLICY['maximum_schema_repairs_total']:return finish('Schema_repair_exhausted')
                        repairs+=1;error=exc
                        if isinstance(locals().get('output'),dict):
                            badname=(output.get('action')or{}).get('tool_name')
                            restricted=[t for t in tools if t['function']['name']==badname]
                            if restricted:repair_tools=restricted
                # Validate the public belief before any expensive local dispatch.
                # This probability has assimilated previous tool results only.
                preview=parse_belief_update(args,BeliefState())
                preview.step=step
                if name=='submit':
                    evidence,state,metadata=dispatch_tool(name,args,state,db,str(log.directory))
                    latest=float(state.p);latest_step=step
                    log('belief_validated',{'step':step,'probability':latest})
                    log('scientific_action',{'step':step,'tool':name,'public_belief':state.to_dict(),'evidence_sha256':sha(evidence)})
                    log('submitted',{'probability':latest,'actions':step,'requests':client.calls,'seconds':time.monotonic()-started,'fallback':False})
                    return latest
                latest=float(preview.p);latest_step=step
                log('belief_validated',{'step':step,'probability':latest})
                if step==POLICY['maximum_valid_actions']:return finish('Maximum_readout_actions')
                if time.monotonic()>=deadline-POLICY['finalization_margin_seconds']:return finish('Before_tool_deadline')
                if db is None:db=db_factory(inp,labels)
                evidence,state,metadata=dispatch_tool(name,args,state,db,str(log.directory))
                completed_retrievals+=1
                log('scientific_action',{'step':step,'tool':name,'public_belief':state.to_dict(),'evidence_sha256':sha(evidence)})
                if time.monotonic()>=deadline-POLICY['finalization_margin_seconds']:return finish('After_tool_deadline')
                call_id='typed-'+str(step)
                messages.extend([{'role':'assistant','content':'','tool_calls':[{'id':call_id,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},
                    {'role':'tool','tool_call_id':call_id,'content':evidence},
                    {'role':'user','content':state.to_prompt_str(5)+'\nConsider the new tool result when updating your next belief.'}])
                seen=len(messages)-3
            return finish('No_later_action')
    except InferenceDeadline:return finish('Inference_deadline')
    except BudgetError:raise
    except Exception as exc:return finish(type(exc).__name__)
    finally:
        from ble15_runtime import close_readonly_database
        close_readonly_database(db,log)
        budget=getattr(client,'run_budget',None)if client is not None else None
        if budget is not None and hasattr(budget,'owned_request_ids'):
            budget.close_uncertain_local_requests(budget.owned_request_ids)
