"""Outcome-blind historical A0 payload construction; no inference transport."""
import json
from agent.prompts import format_question_prompt
from agent.tools import SUBMIT_TOOL
from r1api.question import build_question
from r1api.predictor import matching_labels
def a0_payload(inp,labeled):
    labels=matching_labels(inp,labeled)
    text=format_question_prompt(build_question(*inp,labeled=labels))
    return json.dumps({'available_ble_tools':[SUBMIT_TOOL],'new_public_messages':[{'role':'user','content':text}],'force_submit':True,'semantic_backend':'none'},ensure_ascii=False)
