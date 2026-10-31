# Attribution and licensing review

## Original BLE and organizer scaffold

Stanford AIMS Foundations / PAIEC Predictor Baselines contributors:
https://github.com/aims-foundations/paiec_baseline,
commit `cc88a959c1e5e7462f31a9215baba066ce6d6e2b`.

The upstream code is MIT licensed. The original complete notice is preserved in
`submission/UPSTREAM_LICENSE.txt`, and the root MIT notice credits both the upstream
contributors and Karim Ghandour. The original source tree is not wholesale bundled;
the required baseline modules and our frozen adaptations are under `submission/`.
The whitelist/hash manifest identifies the actual selected implementation, which
includes local changes relative to upstream. Credit for BLE's architecture and
retrieval methodology remains with AIMS Foundations.

Our source, adapters, experimental methods and release material use MIT. This
does not imply ownership of upstream BLE or a relicense of external assets.

## Dependencies and excluded assets

NumPy, Pandas, PyArrow, PyTorch, SentenceTransformers, Transformers, Tokenizers,
Safetensors, Hugging Face Hub and SciPy remain separate dependencies under their
own licenses/notices; no third-party library source or wheels are vendored.

Measurement DB and its benchmark sources have heterogeneous terms. No dataset
rows, traces, images, audio, derived SQL/vector corpus or protected labels are
redistributed here. Pinned identifiers and hashes are provenance only. Operators
must review applicable terms for data they obtain separately.

MiniLM and EmbeddingGemma weights are not bundled. Their identifiers/revisions
document the actual methods; they do not grant redistribution rights. OpenAI and
Google model names identify providers, not affiliation or endorsement. API and
subscription access remain subject to their providers' applicable terms.

## Review conclusion

The released code can use MIT while preserving the upstream notice. The release
does not assert that private retrieval assets are universally redistributable;
withholding them avoids extending code-license conclusions to data/model rights.
This is a provenance/compliance inventory for the included files, not a blanket
legal clearance for any external dataset a user later downloads.
