"""Official PAIEC entry point for the full frozen R1 production attempt."""
import json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
# Same private root configuration and import order as validated AIMS boundary.
try:
 _cfg=json.loads((HERE/'submission_config.json').read_text())
 for _k,_v in (_cfg.get('api_keys')or{}).items():
  if _k=='OPENAI_API_KEY'and _v and not os.environ.get(_k):os.environ[_k]=_v
except(OSError,ValueError):pass
from production import predict
