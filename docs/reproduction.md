# Reproduction modes

## 1. Offline notebook and aggregate analysis

Install requirements-notebook.txt using Python 3.12 with SQLite FTS5. Run
python scripts/verify_notebook.py from the repository root. No notebook cell
downloads anything, reads credentials, contacts a provider, or uses hidden
evaluation outcomes. Fixture labels and model replies are invented. The example
uses an SQLite temporary directory and the exact runtime filtering and
coordinator code. It substitutes the database and HTTP endpoint explicitly.

Use python scripts/validate_release.py to validate source hashes, disclosures and
release hygiene. Use python -m unittest discover -s tests/hosted_ble15a -p test_hosted_ble15a.py
for the focused synthetic test suite, and python scripts/verify_results.py for the
historical public aggregate checks. The broader historical test suite has separate
requirements-dev.txt and optional protected-fixture gates. Install its dependencies
separately if you need that archive's tests.

## 2. Restored scored source and separately authorized real inference

Start at [the exact asset list](../hosted-ble15a/README_OPENREVIEW.md). Restore
the credential-free full archive in a private scratch directory with about 9 GB
free. Check original asset digests and run the official checker and smoke test
as documented there. Its configuration prevents live inference. The public
MiniLM source is pinned and was fetched and hash-verified previously. The six
derived files require an authorized exact copy. Gated raw Measurement DB access
alone has no verified exact derivation path.

Live inference requires an explicit decision outside the notebook, an authorized
private copy of the reconstructed directory, approved asset access, the user's own
credential supplied through a secure environment and separate spending approval.
Only in that private copy would an operator set enable_paid_inference to true and
use the actual model.predict entry point with permitted inputs. Keep credentials
out of notebooks, Git, archives and logs. Consult current official provider pricing
and limits before any call. No live command is run by this release.

Frozen guard values are engineering caps, not a bill estimate or a project cap.
They allow up to $1 reserved per forecast and $50 per shared execution scope,
with at most four requests per forecast and a reserved output envelope. Actual
cost depends on input/output tokens, cache behavior and prices. Restarts or
separate scopes can multiply exposure. Hosted throughput, replay count and cost
cannot be derived from the final score. A new API run can also differ with model
service state, platform timing, or hardware.

The scorer's private target labels, evaluation order and runtime accounting are
not publicly available. Source verification and offline mocked execution do not
reproduce the hosted ALC. [OpenAI API pricing](https://openai.com/api/pricing/) ·
[PAIEC rules and kit](https://aims.stanford.edu/competition)
