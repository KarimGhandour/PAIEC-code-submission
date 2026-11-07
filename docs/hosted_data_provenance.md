# Data, assets and licenses for hosted-ble15a

- Exact original and public-safe runtime member identities, size, disposition and
  hashes are in [ARTIFACT_MANIFEST.json](../hosted-ble15a/ARTIFACT_MANIFEST.json).
- [UPSTREAM_DATA_INVENTORY.json](../hosted-ble15a/UPSTREAM_DATA_INVENTORY.json)
  pins the gated Measurement DB research snapshot and raw file hashes. Raw
  availability does not imply access to the exact derived assets. AIMS curation
  and third-party benchmark content have separate license boundaries.
- The frozen [source-specific ledger](../hosted-ble15a/runtime/data/RETRIEVAL_ELIGIBILITY_AND_LICENSES.json)
  carries original benchmark provenance and eligibility decisions. Scoring use
  does not establish public redistribution rights for the exact derived files.
- MiniLM is Apache-2.0 at the pinned revision in the artifact manifest. Its public
  Safetensors weight and all configuration files are individually hash-bound.
  No weights are distributed here. The bundled model metadata retains its notice.
- The XZ corpus, SQLite traces, semantic vectors and item map, protected inputs
  and firewall cache are omitted. Do not publish them without exact source and
  disclosure clearance. The selected ZIP remains private.
- The [hosted aggregate release](../results/hosted_ble15a_aggregates/) uses ordinal
  G1–G9 labels. It contains no hidden outcomes or reverse mappings. The historical
  public research analysis uses published loss cells only. The approved diagram
  provenance is recorded in [figures/PROVENANCE.json](../figures/PROVENANCE.json).
  The teaching fixture was invented and contains no competition examples.

[Measurement DB license and access](https://huggingface.co/datasets/aims-foundations/measurement-db#license) ·
[Pinned MiniLM revision](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/c9745ed1d9f207416be6d2e6f8de32d1f16199bf)
