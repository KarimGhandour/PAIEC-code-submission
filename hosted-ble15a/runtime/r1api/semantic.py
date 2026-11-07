import json,re
import numpy as np
from pathlib import Path
from .util import features
def representation(f,it):
 text=it.get('content') or '';ff=features(it.get('item_features') or '');complete=not bool(it.get('asset_manifest'))
 if f=='babilong':
  try:
   o=json.loads(text);config=o.get('prompt_configuration',{});text=json.dumps({'representation':'BABILong retrieval approximation; full context is not embedded','task':config.get('instruction',''),'question':o.get('question',''),'context_length_metadata':{k:v for k,v in ff.items() if re.search('length|context|task',k,re.I)},'answer_format':config.get('post_prompt','')},ensure_ascii=False)
  except (ValueError,TypeError):text=text[:3000]
  complete=False
 # Stable head+tail representation before256-token MiniLM truncation, not just first256 of huge context.
 if len(text)>2400:text=text[:1700]+'\n[...middle omitted in retrieval representation...]\n'+text[-600:]
 return text,complete

_ENCODER=None
_TOKENIZER=None

def encode(texts):
 global _ENCODER,_TOKENIZER
 import torch
 if _ENCODER is None:
  from transformers import AutoModel,AutoTokenizer
  root=Path(__file__).resolve().parents[1]/'models/minilm'
  cfg=json.loads((root/'1_Pooling/config.json').read_text())
  if cfg.get('word_embedding_dimension')!=384 or not cfg.get('pooling_mode_mean_tokens') or any(cfg.get(k,False) for k in ['pooling_mode_cls_token','pooling_mode_max_tokens','pooling_mode_mean_sqrt_len_tokens']):raise ValueError('Frozen pooling configuration differs')
  if json.loads((root/'sentence_bert_config.json').read_text()).get('max_seq_length')!=256:raise ValueError('Frozen sequence length differs')
  torch.set_num_threads(4)
  _TOKENIZER=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
  _ENCODER=AutoModel.from_pretrained(str(root),local_files_only=True,trust_remote_code=False).to('cpu').eval()
 single=isinstance(texts,str)
 values=[texts]if single else list(texts)
 if not values:return np.empty((0,384),dtype=np.float32)
 outputs=[]
 # Match SentenceTransformer's per-string whitespace policy.
 for start in range(0,len(values),32):
  batch=[str(x).strip()for x in values[start:start+32]]
  features=_TOKENIZER(batch,padding=True,truncation=True,max_length=256,return_tensors='pt')
  with torch.inference_mode():
   embeddings=_ENCODER(**features,return_dict=True).last_hidden_state
   mask=features['attention_mask'].unsqueeze(-1).expand(embeddings.size()).to(embeddings.dtype)
   vectors=(embeddings*mask).sum(1)/mask.sum(1).clamp(min=1e-9)
   # Frozen modules.json includes a Normalize module; encode also requests
   # normalization, so reproduce both operations rather than collapsing them.
   modules=json.loads((Path(__file__).resolve().parents[1]/'models/minilm/modules.json').read_text())
   if [x['type'].rsplit('.',1)[-1]for x in modules]!=['Transformer','Pooling','Normalize']:raise ValueError('Frozen encoder module sequence differs')
   vectors=torch.nn.functional.normalize(vectors,p=2,dim=1)
   vectors=torch.nn.functional.normalize(vectors,p=2,dim=1)
  outputs.append(vectors.cpu().numpy())
 result=np.concatenate(outputs,axis=0)
 return result[0]if single else result
