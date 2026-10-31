"""Codabench root entry point; separate state and audit directory for every forecast."""
import os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
for path in [HERE,HERE/'src']:
    if str(path) not in sys.path:sys.path.insert(0,str(path))
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
from r1api.predictor import forecast
from r1api.assets import hydrated_corpus
# Worker import precedes the official per-predict deadline. One shared,
# verified materialization survives worker/checkpoint restarts.
hydrated_corpus()

def predict(input: list[dict], labeled: list=None) -> float:
    return forecast(input,labeled)
