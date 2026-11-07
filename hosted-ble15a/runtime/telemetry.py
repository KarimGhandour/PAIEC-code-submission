"""Sanitized engineering observations; never log target text or generated rationale."""
from contextlib import contextmanager
import math,time
from r1api.predictor import Journal

def number(v):return type(v)in(int,float)and math.isfinite(v)
def tokens(value):
    if not isinstance(value,dict):return{}
    result={}
    for k in ['input_tokens','output_tokens','total_tokens','reasoning_tokens','cached_tokens','cache_write_tokens','ttl_30m_tokens','ttl_12h_tokens']:
        if type(value.get(k))is int and value[k]>=0:result[k]=value[k]
    for k in ['input_tokens_details','output_tokens_details','cache_write_tokens_details']:
        if isinstance(value.get(k),dict):result[k]=tokens(value[k])
    return result

class SanitizedJournal(Journal):
    def __call__(self,kind,data):
        # Whitelist fixed controller metadata, never raw prompt/action/evidence text.
        safe={}
        for k in ['request','step','repair','actions','requests','acquired_labels','input_items','request_bytes','attempt','http_status']:
            if type(data.get(k))is int:safe[k]=data[k]
        for k in ['started_at','ended_at','seconds','probability']:
            if number(data.get(k)):safe[k]=data[k]
        for k in ['fallback','retryable','known_CONNECT_rejection','tier_downgraded']:
            if type(data.get(k))is bool:safe[k]=data[k]
        for k in ['client_request_id','server_request_id','input_sha256','acquisition_prefix_sha256','request_sha256','response_sha256','evidence_sha256']:
            if isinstance(data.get(k),str)and len(data[k])<=180:safe[k]=data[k]
        # These are controlled enum/class strings, not library/model exception text.
        for k in ['stage','reason','completion_status','category','response_id','requested_model','returned_model','reasoning_effort','requested_service_tier','actual_service_tier']:
            if isinstance(data.get(k),str)and len(data[k])<=100:safe[k]=data[k]
        for k in ['maximum_reserved_usd','cumulative_reserved_usd','published_standard_estimate_usd','known_usage_upper_usd','cumulative_known_usage_upper_usd','uncertain_request_reserve_usd','published_effective_tier_estimate_usd']:
            v=data.get(k)
            if isinstance(v,str)and len(v)<=50:
                try:
                    if math.isfinite(float(v)):safe[k]=v
                except ValueError:pass
        if isinstance(data.get('usage'),dict):safe['usage']=tokens(data['usage'])
        if kind=='scientific_action':
            safe['tool']=data['tool'];b=data.get('public_belief')or{}
            safe['public_belief']={k:b[k]for k in ['p','step']if number(b.get(k))}
            if b.get('confidence')in['low','medium','high']:safe['public_belief']['confidence']=b['confidence']
        if kind=='deployment_tool_timing':safe['tool']=data['tool']
        if kind=='response_received':
            r=data.get('response')or{}
            safe['response']={'id':r.get('id'),'status':r.get('status'),'model':r.get('model'),'service_tier':r.get('service_tier'),'usage':tokens(r.get('usage')),
                'encrypted_reasoning_present':any(v.get('encrypted_content_present')is True for v in r.get('output',[])if v.get('type')=='reasoning')}
        super().__call__(kind,safe)

@contextmanager
def instrument_dispatch(log):
    import r1api.predictor as predictor
    original=predictor.dispatch_tool
    def timed(name,args,state,db,path):
        started=time.monotonic()
        try:return original(name,args,state,db,path)
        finally:log('deployment_tool_timing',{'tool':name,'seconds':time.monotonic()-started})
    predictor.dispatch_tool=timed
    try:yield
    finally:predictor.dispatch_tool=original

def sanitized_details(events):
    requests=[x for x in events if x['event']=='response_received']
    calls=[x for x in events if x['event']=='scientific_action']
    transport=[x for x in events if x['event']=='deployment_transport_attempt']
    tool=[{'tool':x['tool'],'seconds':x['seconds']}for x in events if x['event']=='deployment_tool_timing']
    reasoning=sum((x.get('usage',{}).get('output_tokens_details')or{}).get('reasoning_tokens',0)for x in events if x['event']=='usage')
    return {'successful_continuation_responses':max(0,len(requests)-1),'reasoning_tokens':reasoning,
        'initial_belief_probability':(calls[0].get('public_belief')or{}).get('p')if calls else None,
        'tool_timings':tool,'MiniLM_semantic_tool_requested':any(x.get('tool')=='semantic_search_items'for x in calls),
        'transport_opens':len(transport),'proxy_CONNECT_rejections':sum(x.get('known_CONNECT_rejection')is True for x in transport),
        'API_request_seconds':[x.get('seconds')for x in requests],
        'sanitized_logging':True}
