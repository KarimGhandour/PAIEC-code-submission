# Frozen R1 inference source

These source files were copied directly from the approved compact ZIP. Do not
rename modules, replace prompts, change schemas or alter transport under the label
of exact R1. `scripts/check_source.py` verifies their original SHA-256 values.

- `model.py`: root Codabench `predict()` interface and import-time asset hydration.
- `r1api/predictor.py`: five-action trusted coordinator, per-forecast state and fallback.
- `r1api/responses.py`: Responses API client, Standard/Medium, opaque state retention,
  15-request limit, no automatic retry of uncertain requests and spending envelopes.
- `r1api/db.py`: eight admissibility-filtered SQL/MiniLM retrieval operations.
- `r1api/assets.py`: locked, hash-verified XZ hydration to a private shared cache.
- `r1api/protocol.py`, `src/agent/belief_state.py`, `src/agent/prompts.py`:
  typed action validation, beliefs, frozen prompt and final probability handling.
- `comp_pipeline/script/agent_tools.py`: original retrieval tool contracts.

Copying `config.example.json` alone does not enable R1. First obtain and validate
every required authorized data/model asset; see `../docs/data_provenance.md`.
`python scripts/configure_local.py` from the repository root creates an ignored,
owner-only config with an empty key and paid inference disabled. Environment
`OPENAI_API_KEY` takes precedence over configured key for local use; do not place
credentials in commands, Git, papers or public artifacts. Hosted credential handling
is a separate private competition configuration, not authorized by this release.

The template preserves USD1/forecast, USD25 aggregate and 8192 output-token limits.
Neither these example limits nor publication authorize spending. Each real run needs
the operator's authorization and a unique run identifier. A failed request can retain
its conservative spending reservation. Fallback activations are explicitly logged.

No labeling.py is included: acquisition uses the official default random policy.
Matched labels are conditioned on at budgets 0,1,3,7,15,31. No hidden identity lookup
or cross-forecast history is introduced.
