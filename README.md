# PAIEC | BLE 1.5-A, from belief to forecast

**Codabench #1032237 · formative Brier ALC 0.1590607804 · nine subject–benchmark groups · 489 distinct pairs · six budgets**

Proposed release tag `v1.5.0-rc.1`. See the [release notes](RELEASE_NOTES.md),
[release review](RELEASE_REVIEW.md) and [citation metadata](CITATION.cff).

Predict whether a specified AI system will answer an item correctly without
running that system. Stanford AIMS Foundations supplied the Bayesian Linguistic
Evaluator (BLE) baseline. This project audited the evidence boundary, measured
initial and revised beliefs on a controlled public panel, and delivered a bounded
Responses API implementation for the competition.

**Start with [BLE 1.5-A Explained](notebooks/01_BLE_1_5A_Explained.ipynb).** It
works through scoring, the frozen coordinator, filtered SQLite retrieval, the
public confirmation and the anonymized hosted results. Its synthetic walkthrough
calls the actual controller and request parser with a mock transport. It needs
no inference credentials, model weights or private data.

## Three distinct artifacts

| Label | Role | Location |
|---|---|---|
| hosted-ble15a | Scored Standard/Medium runtime, credential-sanitized | [Frozen source and asset manifest](hosted-ble15a/README_OPENREVIEW.md) |
| research-r1 | Earlier outcome-sealed research and historical release | [Research README](docs/research_r1_readme.md), [historical source](submission/), [v1.0.0-r1](https://github.com/KarimGhandour/PAIEC-code-submission/releases/tag/v1.0.0-r1) |
| experimental-a2-fast | Separate Fast candidate #1033843, failed with an unclassified error | [Decision ledger](results/decision_ledger.csv) |

The public R1 Brier result **0.153728** and hosted A's **0.1590607804 Brier
ALC** use different samples and estimands. The hosted score does not expose
counted runtime, per-forecast API traffic or coverage of native final submits.

## Run the notebook offline

Use Python 3.12 with SQLite FTS5. Install the pinned notebook tools once, then
run from the repository root with networking disabled.

~~~sh
python3.12 -m venv .venv-notebook
. .venv-notebook/bin/activate
python -m pip install -r requirements-notebook.txt
python scripts/verify_notebook.py
python scripts/verify_results.py
~~~

The notebook check executes in a fresh Jupyter kernel and writes an executed
copy and self-contained HTML preview under the ignored `outputs/` directory.
The result checker verifies historical R1 aggregate arithmetic. See
[Reproduction](docs/reproduction.md) for offline execution and the separate
opt-in production setup.

## Inspect or reconstruct scored A

The frozen source under hosted-ble15a/runtime/ comes from the verified
supplement. Its configuration has an empty key map and paid inference off.
Exact reconstruction needs the public pinned MiniLM weight and **six
authorized derived data and firewall files**. The supplement alone fails
closed on the missing corpus. No independent byte-matching data regeneration
or public distribution route has been verified. If you have authorized exact
copies, follow the [reconstruction commands](hosted-ble15a/README_OPENREVIEW.md).

- [Architecture](docs/architecture.md) and [deployment reliability](docs/deployment_reliability.md)
- [Data and licenses](docs/hosted_data_provenance.md) and [source equivalence](docs/release_manifest.md)
- [Scientific claims ledger](docs/scientific_claims.md) and [experiment decisions](results/decision_ledger.csv)
- [Paper and citation](paper/README.md) and [notebook design rationale](docs/notebook_design.md)

This is a local release candidate. The public remote and scored artifacts were
preserved. The supplied technical report and supplementary artifact remain
subject to scientific/editorial and organizer review as applicable.
