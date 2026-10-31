# Codex research transport versus Responses API deployment

Historical experiments used Plus-authenticated Codex CLI with Medium reasoning,
fresh forecasting sessions, same-session continuation inside a forecast and an
external Python retrieval coordinator under Seatbelt. Hidden Codex instructions,
provider snapshots and harness behavior are not fully reproducible through an API.
Subscription access is not API billing or model equivalence.

The selected standalone implementation instead uses `api.openai.com/v1/responses`,
`gpt-6-luna`, `reasoning={mode:standard, effort:medium}`, no native API tool calls,
strict typed JSON actions, `store=false`, and returned encrypted reasoning items
replayed intact in subsequent request inputs. The trusted coordinator still executes
the eight tools and applies five scientific actions, with bounded schema repair,
no automatic uncertain transport retry and a maximum of 15 requests.

One genuine historical CRUXEval/GPT-3.5 budget-seven API forecast completed during
LIVE TEST 002, including retrieval, belief revision and submission. This proves
technical end-to-end operation for that case, not predictive API equivalence or
hidden-test quality. Native encrypted reasoning payloads, credentials and session
logs are deliberately absent from this public repository.

The compact/full audit found exact parity on 153 deterministic archived trajectories,
510 request bodies, 1,028 retrieval calls, 11,497,074 retained SQL rows and 2,255,645
retained traces. Its mock outputs were frozen actions, not new inference. The audit
supports algorithm/evidence equivalence, not stochastic output or statistical
Brier equivalence. Neither that audit nor this code release reproduces 0.153728
through the Responses API.

Compact deployment adds XZ materialization and a hash-bound shared cache. It needs
about 6.77 GB of decoded SQL space. Asset/cache failure can occur during root import,
before predictor fallback; overall deadlines include initialization. Actual worker
classification, API limits, hosted resource contention, fallback frequency and
hidden-test scores require hosted observations. No hosted success is asserted here.
