"""Offline checks for the released scored runtime and its pedagogical fixture."""
import hashlib
import json
from pathlib import Path
import unittest

from examples.offline_walkthrough import RUNTIME, TARGET, LABELS, run_demo, typed_action
from r1api.predictor import TOOLS
from r1api.predictor_common import matching_labels
from r1api.protocol import SyntaxFailure, decode
from r1api.responses import APIError, ResponsesClient


class HostedRelease(unittest.TestCase):
    def test_exact_bundled_hashes_and_no_live_default(self):
        meta = json.loads((RUNTIME.parent / "ARTIFACT_MANIFEST.json").read_text())
        for entry in meta["members"]:
            file = RUNTIME / entry["path"]
            if entry["delivery"] == "bundled":
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), entry["sha256"])
            else:
                self.assertFalse(file.exists())
        cfg = json.loads((RUNTIME / "submission_config.json").read_text())
        self.assertEqual(cfg["api_keys"], {})
        self.assertIs(cfg["enable_paid_inference"], False)
        with self.assertRaises(APIError):
            ResponsesClient({"enable_paid_inference":False, "max_forecast_usd":1}, lambda *_: None)

    def test_actual_filtered_aggregation_and_readouts(self):
        out = run_demo()
        self.assertEqual(out["eligible"], ["relevant","weak"])
        self.assertEqual((out["evidence"]["successes"],out["evidence"]["trials"]), (9,20))
        self.assertEqual(out["runs"]["Final submit"]["beliefs"], [.55,.68])
        self.assertEqual(out["runs"]["Interrupted after valid belief"]["readout"], "intermediate_return")
        self.assertEqual(out["runs"]["Interrupted before valid belief"]["readout"], "fallback")

    def test_typed_probability_and_acquisition_boundaries(self):
        self.assertEqual(decode(typed_action("submit",.68),TOOLS)[1]["probability"],.68)
        with self.assertRaises(SyntaxFailure):
            decode(typed_action("submit",-0.01),TOOLS)
        unrelated = [[TARGET[0], {"benchmark_id":"unrelated","item_content":"Toy other task"}], 1]
        self.assertEqual(matching_labels(TARGET,LABELS+[unrelated]), LABELS)
        with self.assertRaises(ValueError):
            matching_labels(TARGET, LABELS*32)


if __name__ == "__main__":
    unittest.main()
