# Data provenance, eligibility and missing assets

Official sources:

- Baseline: https://github.com/aims-foundations/paiec_baseline at
  `cc88a959c1e5e7462f31a9215baba066ce6d6e2b`.
- Measurement DB: https://huggingface.co/datasets/aims-foundations/measurement-db at
  `54074453da7b9911be0f48e4c560be547bc84d21`.
- Retrieval encoder: sentence-transformers/all-MiniLM-L6-v2 at
  `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`, 384 dimensions.
- Separate rejected factor experiment encoder: google/embeddinggemma-2 at
  `21ad7b3a498496f5c3e5de0d9afecd706e172a04`, frozen text/code-only 270M configuration.

All are distinct from hidden runtime benchmark identities. The code does not
reverse-map anonymous evaluation IDs. Gold/evaluation outcomes are not retrieval
inputs. Per-source restrictions, public release status and binary-correctness
eligibility matter; availability in a local download or competition ZIP does not
grant general redistribution rights.

Only file/revision/hash metadata is published. No Measurement DB rows, derived
SQL, vectors, traces, protected input manifests, model weights or private frozen
predictions are bundled. The MIT code license does not apply to these external assets.

`scripts/prepare_data.py` prints the pinned source-file inventory without downloading.
It can selectively retrieve a family after explicit flags, reusing the HF cache and
verifying sizes/checksums. It never asks for or prints tokens. Existing HF login
credentials can be used subject to dataset approval and source terms. Large
downloads require an operator-selected byte bound; no download occurred while
preparing this release.

**Downloading public tables does not recreate the exact frozen evidence bundle.**
That bundle also needs the original eligible-item/source mapping, protected input
manifest and deterministic historical preparation. Protected contents are withheld.
Its complete asset hashes are in `artifacts/manifests/private_assets.json`; the
installer validates a separately authorized local bundle and makes no network calls.
Do not obtain assets by publishing or exchanging the private credential-bearing ZIP.

The selected corpus contains 62 benchmark cards, global keyword text and a fixed
MiniLM index. Frozen excluded-family numerical rows were omitted, while excluded
text needed for duplicate checks/global BM25 statistics was retained. Compact
storage preserves tool-visible 4,000-character trace prefixes, original full hashes
and truncation flags. Runtime input and acquisition labels can add exclusions,
never remove frozen ones. Source protections are integral to R1, not optional
download filters.

Exact preparation is therefore a **restricted-asset reproducibility limitation**.
The release provides exact runtime readers, source-file download metadata, asset
integrity installation, public synthetic tests and method/analysis code. It does
not promise a one-command regeneration of the private corpus from public metadata.
Rebuilding a different corpus should be labeled a new reproduction and audited
before comparing predictive performance.
