"""Portable no-network root-interface/synthetic-retrieval smoke test. No real forecasts."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'submission'),str(ROOT/'submission/src')]
from test_public_release import PublicReleaseTests
suite=unittest.TestSuite(PublicReleaseTests(n) for n in ['test_root_interface_all_six_budgets_with_mock_transport','test_synthetic_eight_tools_and_source_exclusion','test_exact_source_and_prompt_hash'])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
