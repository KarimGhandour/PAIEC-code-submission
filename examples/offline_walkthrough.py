"""Invented PAIEC records executed through the frozen scored-A controller."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import sys
import tempfile

RUNTIME = Path(__file__).resolve().parents[1] / "hosted-ble15a/runtime"
sys.path[:0] = [str(RUNTIME), str(RUNTIME / "src")]
from r1api.db import AuditedDB
from r1api.predictor import forecast
from r1api.responses import APIError, ResponsesClient
from r1api.util import content_hash

SUBJECT = {"normalized_name": "Toy solver", "harness": "toy-v1"}
TARGET = [SUBJECT, {"benchmark_id": "toy-math", "item_content": "Find a modular inverse."}]
LABELS = [[[SUBJECT, {"benchmark_id": "toy-math", "item_content": "A distinct revealed exercise."}], 1]]
ROWS = (
    (1, "relevant", "g-related", "s-related", "Compute a modular inverse by Euclid.", 7, 10),
    (2, "weak", "g-weak", "s-weak", "Count vertices in a tree.", 2, 10),
    (3, "target-copy", "g-protected", "s-protected", TARGET[1]["item_content"], 10, 10),
    (4, "source-sibling", "g-protected", "s-protected", "A sibling variant in the same source.", 10, 10),
)


def create_fixture(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
        CREATE TABLE items(id INTEGER PRIMARY KEY, family, iid, source_group, source_key, content, content_hash);
        CREATE VIRTUAL TABLE item_fts USING fts5(content);
        CREATE TABLE benchmarks(family, card);
        CREATE TABLE subjects(family, sid, name, normalized, config);
        CREATE TABLE pair_stats(family, sid, cond, iid, k, n);
        INSERT INTO benchmarks VALUES ('toy-math', '{}');
        INSERT INTO subjects VALUES ('toy-math', 'toy-peer', 'Toy peer', 'toypeer', '{}');
        """)
        for idx, iid, group, key, text, k, n in ROWS:
            db.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?)", (idx,"toy-math",iid,group,key,text,content_hash(text)))
            db.execute("INSERT INTO item_fts(rowid,content) VALUES (?,?)", (idx,text))
            db.execute("INSERT INTO pair_stats VALUES ('toy-math','toy-peer','plain',?,?,?)", (iid,k,n))


class TeachingJournal:
    def __init__(self, directory):
        self.directory = directory
        self.events = []

    def __call__(self, event, fields):
        self.events.append((event, fields))


def typed_action(name, probability):
    belief = dict(p=probability, confidence="medium", update_reasoning="Synthetic teaching belief.",
                  base_rate_anchor=None, evidence_for=None, evidence_against=None, key_uncertainties=None)
    if name == "get_scores":
        args = dict(benchmark_id="toy-math", model=None, test_condition=None, updated_belief=belief)
    else:
        args = dict(probability=probability, reasoning="Synthetic teaching finalization.", updated_belief=belief)
    return {"action": {"tool_name": name, "arguments": args}}


def inspect_retrieval(path):
    with closing(AuditedDB(path=path, targets=[{"input": TARGET}])) as db:
        eligible = [r[0] for r in db.c.execute("SELECT iid FROM permitted_items ORDER BY id")]
        evidence = json.loads(db.get_scores("toy-math"))["evidence"][0]
    assert eligible == ["relevant", "weak"]
    assert (evidence["successes"], evidence["trials"]) == (9, 20)
    return eligible, evidence


def simulate(path, journal, *, interrupt_at=None):
    received = []

    def post(body, timeout):
        assert body["model"] == "gpt-6-luna" and body["reasoning"]["effort"] == "medium"
        assert body["tools"] == [] and body["service_tier"] == "default"
        assert body["store"] is False and body["include"] == ["reasoning.encrypted_content"]
        assert 0 < timeout <= 20
        step = len(received)
        if step == interrupt_at:
            raise APIError("Synthetic transport interruption", stage="mock")
        if step:
            assert all(item in body["input"] for item in received[-1])
            assert "get_scores" in body["input"][-1]["content"]
        action = typed_action("get_scores" if step == 0 else "submit", .55 if step == 0 else .68)
        output = [
            {"type": "reasoning", "id": f"toy-{step}", "encrypted_content": "synthetic-opaque-marker"},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": json.dumps(action)}]},
        ]
        received.append(output)
        return {"id": f"toy-{step}", "model": body["model"], "status": "completed",
                "service_tier": body["service_tier"], "output": output,
                "usage": {"input_tokens": 100, "output_tokens": 40}}

    cfg = {"enable_paid_inference": False, "max_forecast_usd": 1, "max_output_tokens": 8192}
    return forecast(
        TARGET, LABELS, config=cfg, journal=journal,
        client_factory=lambda config, log: ResponsesClient(config, log, post=post),
        db_factory=lambda inp, labels: AuditedDB(path=path, targets=[{"input": inp}]),
    )


def run_demo():
    with tempfile.TemporaryDirectory(prefix="paiec-synthetic-") as temp:
        root = Path(temp)
        fixture = root / "toy.sqlite"
        create_fixture(fixture)
        eligible, evidence = inspect_retrieval(fixture)
        runs = {}
        for name, failure, expected, marker in [
            ("Final submit", None, .68, "submitted"),
            ("Interrupted after valid belief", 1, .55, "intermediate_return"),
            ("Interrupted before valid belief", 0, 5/9, "fallback"),
        ]:
            log = TeachingJournal(root)
            probability = simulate(fixture, log, interrupt_at=failure)
            assert abs(probability - expected) < 1e-12, (name, [event for event, _ in log.events])
            assert any(event == marker for event, _ in log.events)
            runs[name] = {
                "probability": probability, "readout": marker,
                "beliefs": [v["probability"] for kind, v in log.events if kind == "belief_validated"],
                "actions": [v["tool"] for kind, v in log.events if kind == "scientific_action"],
            }
    return {"eligible": eligible, "evidence": evidence, "runs": runs}
