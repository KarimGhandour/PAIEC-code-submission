# PAIEC OpenReview supplement for scored BLE 1.5-A

**This is a source-plus-asset reconstruction package.** The original private
Codabench executable archive exceeds the form's 100 MB limit.

| Scored artifact | Value |
|---|---|
| Selected Codabench submission | 1032237 (Finished) |
| Official formative Brier ALC | 0.1590607804 |
| Original artifact | PAIEC_BLE15_A_PRODUCTION_001.zip |
| Original size | 695,451,321 bytes |
| Original SHA-256 | 90a6a22560328e4ff5ec3f86375dbf567aecf802d2632fe6829878b339be7c3c |

The original ZIP stores a 382 MB XZ-compressed SQLite corpus, a 311 MB trace
SQLite database, the 90.9 MB MiniLM weight file, and the semantic index. It
also contains an API credential. This supplement fits the upload limit.
Its container and configuration differ from those of the original submission.

## Omitted assets and acquisition

| Exact member | Bytes when unpacked | Source |
|---|---:|---|
| data/evidence.xz.bin | 382,120,380 | Authorized exact asset handoff or private original |
| data/traces_chunked.sqlite | 311,312,384 | Authorized exact asset handoff or private original |
| models/minilm/model.safetensors | 90,868,376 | Pinned public MiniLM repository below |
| data/semantic_vectors.npy | 21,195,392 | Authorized exact asset handoff or private original |
| data/semantic_items.json | 4,914,337 | Authorized exact asset handoff or private original |
| data/protected_inputs.json | 547,490 | Authorized exact asset handoff or private original |
| data/firewall_static_cache.json | 6,177 | Authorized exact asset handoff or private original |

The only pretrained weight file is Safetensors from
[sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/c9745ed1d9f207416be6d2e6f8de32d1f16199bf)
at revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf (Apache-2.0). Its SHA-256
is 53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db.
The manifest lists SHA-256 values for every model file. The exact scored
models.txt retains the plain repository ID required by the official checker.
The reconstruction script applies the revision and hash pin separately.

The gated [Measurement DB](https://huggingface.co/datasets/aims-foundations/measurement-db)
at revision 54074453da7b9911be0f48e4c560be547bc84d21 is the upstream research
input. Request access through that page and observe the source restrictions.
UPSTREAM_DATA_INVENTORY.json records file names, sizes and hashes. With
authorized Hub access, retrieve files by repository, path and pinned revision,
for example with hf download and its --repo-type dataset and --revision flags.
These are raw upstream inputs. No verified public build pipeline or authorized
public URL supplies the exact derived corpus, traces, index, and protected
research masks. Obtain exact copies from the authors or organizers only
through a separately approved channel. Keep the credential-bearing original
archive private.

## Local reconstruction and official checks

Use Python 3.11+ on a POSIX system, with approximately 9 GB of free working
space for the rebuilt ZIP, unpacked runtime and hydrated SQLite corpus.

~~~sh
python3 reconstruct.py --asset-dir /path/to/authorized-exact-assets \
  --fetch-minilm --output BLE15_A_RECONSTRUCTED_OFFLINE.zip
~~~

Use the original relative paths in the asset directory. For fully offline
reconstruction, provide the pinned weight in that directory and omit
--fetch-minilm. An authorized holder of the original private ZIP may instead
restore omitted assets locally:

~~~sh
python3 reconstruct.py --scored-archive /private/path/PAIEC_BLE15_A_PRODUCTION_001.zip \
  --output BLE15_A_RECONSTRUCTED_OFFLINE.zip
~~~

The script verifies the private archive hash when supplied and copies only
omitted assets from it. It validates the sizes and SHA-256 values of every
member, regenerates PACKAGE_HASHES.json and refuses to overwrite output.
It does not read the private config. The output has paid inference disabled.

Download the official starting kit via the [PAIEC competition page](https://aims.stanford.edu/competition).
The scored requirements.txt assumes the evaluator's preinstalled stack.
OFFLINE_VALIDATION_DEPENDENCIES.txt records observed local versions. Use
SQLite with FTS5. The scored archive has no labeling.py, so the platform
uses default acquisition and the predictor consumes the supplied labels.

~~~sh
python3 /path/to/official-kit/tools/check_submission_zip.py BLE15_A_RECONSTRUCTED_OFFLINE.zip
python3 -m zipfile -e BLE15_A_RECONSTRUCTED_OFFLINE.zip rebuilt
env -u OPENAI_API_KEY HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python3 /path/to/official-kit/tools/run_smoke_test.py --concurrency 4 rebuilt
~~~

Run these checks offline. The official smoke uses the local smoke branch.
Live use would require separately authorized credentials and spending approval.

## Verification boundary

With the exact assets, **70 of 72 restored members are byte-identical** to
the scored archive. The differences are submission_config.json (credential
removed and paid inference disabled) and PACKAGE_HASHES.json (regenerated).
ZIP metadata may differ. The sanitized configuration intentionally prevents
live forecasts by default. Source, retrieval assets, masks and scientific
settings are otherwise unchanged.

RECONSTRUCTION_VALIDATION.json records the official checker and smoke on the
full rebuilt archive and the offline six-budget technical gate using real
MiniLM/SQLite and mocked responses. These checks do not rerun the hosted
score or establish public availability of the derived inputs. If OpenReview
requires the identical uploaded container, organizer confirmation is needed
to resolve the size and credential conflict.
