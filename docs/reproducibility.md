# Reproduction and availability

## What runs without restricted assets

Use the README environment instructions. Then:

```sh
python scripts/check_source.py
python scripts/offline_smoke.py
python -m unittest discover -s tests -v
python scripts/verify_results.py
python scripts/prepare_data.py --family algotune
python scripts/score_records.py --help
python -m experiments.inductive_mf_001.run_transfer --help
python scripts/install_private_assets.py --help
python scripts/scan_release.py
```

Source checking verifies the exact selected source bytes. Smoke exercises the
actual root interface and coordinator using **synthetic** assets/actions, real
synthetic SQLite/FTS/Parquet retrieval and mocked query vectors. No released smoke
fixture is represented as historical Measurement DB evidence or a real forecast.
The missing-asset failure test intentionally confirms a genuine data dependency.

The inherited offline R1 and transport regression suites are included with portable
paths. Four tests that need historical private evidence/native records are explicit
skips, not fabricated replacements. Separate synthetic retrieval/state tests cover
their public-testable mechanisms. Additional retained deployment tests cover shared
spending reservations and asset corruption. API/retrieval tests deny socket
connections; the numerical method tests contain no inference or download code.
The factor test trains only a tiny invented numerical fixture; no pretrained model
is downloaded, embedded or fine-tuned and no historical experiment is rerun.

## Availability by study

| Study | Released method/settings | Released records | Numerically verifiable here | Not reproducible from public material alone |
|---|---|---|---|---|
| Audited BLE A0/R1/R2 | exact R1 inference source, R2 policy, original scorer/bootstrap, development/confirmation protocols | aggregate losses, decomposition/reference intervals, provenance hashes | point-score aggregation, development/confirmation means and gain decomposition | original task/prompts/acquisition prefix replay, row-level scoring, original bootstrap, historical Codex forecasts |
| Ledger | exact ledger functions, frozen selection gates, original equal-family scorer/bootstrap | aggregate cells, family/budget reference results | combined point scores and gate arithmetic | matched original source-group bootstrap and raw belief/count audit |
| MF-001 | rank-16 fit/metadata/MAP/scalar functions, fixed settings, complete historical algorithm snapshot | aggregate reference metrics; no embeddings/checkpoints/labels | reference gain arithmetic, synthetic numerical regression | exact held-item/transfer rerun without original arrays/groups and frozen encoder cache |
| Xhigh | frozen effort-only protocol, readout rule, original scorer/bootstrap | aggregate cells, reference uncertainty/sensitivity | Medium/xhigh point scores and direction of gain | new xhigh sessions, original grouped bootstrap and native token audit |

The aggregate cells omit item/source/subject identifiers, outcomes, probabilities,
task text and raw traces. Loss summaries cannot reconstruct original resampling
units. Reference confidence intervals are retained as **reference results**, not
claimed recomputed from public cells. `scripts/verify_results.py` says this explicitly.

## Scoring authorized private records

`scripts/score_records.py` requires a JSON list of records containing family,
subject_id, source_group, target_id, budget, `ys` (recorded binary trials) and named
method probabilities. Supply only records you are authorized to use, under an
ignored local directory. Use `--estimand original_confirmation` for the historical
confirmation scorer or `--estimand equal_family` for ledger/xhigh. Both point and
paired cluster calculations use the original extracted numerical functions. No
default data path or implicit hidden-outcome read is present.

## Factor transfer with authorized arrays

The portable runner uses the frozen 200-epoch, learning-rate .02, rank-16 method;
it has no tuning or embedding option. Required files:

- Source NPZ: normalized `embeddings_all` (global original item order, N×768),
  `source_indices`, binary source outcome matrix `y`.
- Target-feature NPZ: `target_indices` and `groups` (non-object Unicode strings),
  **no outcomes**.
- Metadata JSON: aligned `source_subjects`, `source_models`, `target_subjects`,
  `target_models`, restricted to nine shared foundation identities.
- Acquisition NPZ: seven target `indices` from distinct original groups and `y`.
- Separate evaluation NPZ: unacquired `indices` and `y`; it is not opened until
  predictions are written and hashed.

Call `python -m experiments.inductive_mf_001.run_transfer --help` for arguments.
Exact historical reproduction additionally requires the frozen acquisition indices,
item order and encoder cache, none of which is supplied. The full historical
algorithm snapshot is text for provenance; it refers to unavailable original
research inputs and is not a falsely advertised one-command public launcher.

Embedding generation was frozen text-only EmbeddingGemma 2, with 8,192-token context
and complete 4,096-token chunks for long inputs, token-weighted mean and normalization.
The historical snapshot records this implementation. Users must separately obtain
compatible encoder weights and source terms; this release does not download them.

## Real R1 inference prerequisites

1. Obtain separately authorized derived assets matching the public integrity manifest.
2. Validate/install them with `install_private_assets.py`; no data transfer is implicit.
3. Create the ignored private config with `configure_local.py`. Paid transport remains OFF.
4. Provide your own credential privately and explicitly authorize spending before
   changing the paid flag or running a genuine forecast.
5. Keep the original source unchanged when claiming exact R1; record any runtime,
   model snapshot, corpus, or protocol divergence as a separate reproduction.

The current release is source-and-analysis reproducibility, not unrestricted access
to every historical scientific record. It does not claim independent regeneration
of 0.153728 API Brier, any hidden score, or successful hosted evaluation.
