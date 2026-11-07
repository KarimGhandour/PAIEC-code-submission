import json,math,copy
from agent.llm_client import _strict_schema, _restore_optional_arguments
class SyntaxFailure(ValueError): pass

def parse(text):
 def bad(v):raise SyntaxFailure('Nonfinite JSON literal '+v)
 try:return json.loads(text,parse_constant=bad)
 except (ValueError,TypeError) as e:raise SyntaxFailure('Invalid JSON syntax') from e

def check(value,schema,path='$'):
 """The exact schema subset emitted below, independently enforced before dispatch."""
 if 'anyOf' in schema:
  good=0
  for s in schema['anyOf']:
   try:check(value,s,path);good+=1
   except SyntaxFailure:pass
  if good!=1:raise SyntaxFailure(path+': no unique permitted action/nullable type')
  return
 typ=schema.get('type');ok={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),'number':type(value) in (int,float) and math.isfinite(value),'integer':type(value) is int,'boolean':type(value) is bool,'null':value is None}
 if typ and not ok.get(typ,False):raise SyntaxFailure(path+': invalid '+str(typ))
 if 'enum' in schema and value not in schema['enum']:raise SyntaxFailure(path+': unsupported value')
 if typ=='object':
  props=schema.get('properties',{});miss=set(schema.get('required',[]))-value.keys()
  if miss:raise SyntaxFailure(path+': missing '+','.join(sorted(miss)))
  if schema.get('additionalProperties') is False and value.keys()-props.keys():raise SyntaxFailure(path+': unexpected fields')
  for k,v in value.items():
   if k in props:check(v,props[k],path+'.'+k)
 elif typ=='array':
  for i,v in enumerate(value):check(v,schema['items'],path+f'[{i}]')
 elif typ=='string' and len(value)<schema.get('minLength',0):raise SyntaxFailure(path+': empty required text')
 elif typ in ('number','integer'):
  if value<schema.get('minimum',-math.inf) or value>schema.get('maximum',math.inf):raise SyntaxFailure(path+': out of range')

def wire_schema(tools):
 from agent.llm_client import _strict_schema
 variants=[]
 for t in tools:
  name=t['function']['name'];args=_strict_schema(t['function']['parameters'])
  def bounds(s):
   if s.get('type')=='object':
    for k,v in s.get('properties',{}).items():
     if k in ['probability','p']:v.update(minimum=0,maximum=1)
     if k in ['reasoning','update_reasoning']:v['minLength']=1
     bounds(v)
   for s2 in s.get('anyOf',[]):bounds(s2)
   if s.get('type')=='array':bounds(s['items'])
  bounds(args)
  variants.append({'type':'object','additionalProperties':False,'properties':{'tool_name':{'type':'string','enum':[name]},'arguments':args},'required':['tool_name','arguments']})
 return {'type':'object','additionalProperties':False,'properties':{'action':{'anyOf':variants}},'required':['action']}

def decode(output,tools):
 check(output,wire_schema(tools));a=output['action']
 try:name,args=validate_action({'tool_name':a['tool_name'],'arguments_json':json.dumps(a['arguments'],allow_nan=False)},tools)
 except (ValueError,TypeError,KeyError) as e:raise SyntaxFailure('Invalid tool arguments: '+str(e)[:200]) from e
 if name=='submit' and not 0<=args['probability']<=1:raise SyntaxFailure('Probability outside [0,1]')
 if not 0<=args['updated_belief']['p']<=1:raise SyntaxFailure('Belief outside [0,1]')
 return name,args

def validate_action(output,tools):
 name=output['tool_name'];definition=next(t['function']['parameters'] for t in tools if t['function']['name']==name)
 args=json.loads(_restore_optional_arguments(output['arguments_json'],definition))
 if len(output['arguments_json'])>64000:raise SyntaxFailure('Tool request too long')
 for k,v in args.items():
  if isinstance(v,str) and len(v)>20000:raise SyntaxFailure('Tool text argument too long')
 if name=='semantic_search_items' and not 1<=args.get('k',8)<=20:raise SyntaxFailure('Semantic k outside budget')
 if name=='get_item' and not 0<=args.get('sample',0)<=5:raise SyntaxFailure('Item sample outside budget')
 return name,args
