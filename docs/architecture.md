# Scored BLE 1.5-A architecture

A subject is a model configuration including its harness. An item is the visible
task plus metadata. The organizer's worker invokes predict([subject,item], labeled)
and expects one finite probability. The archive has no labeling.py, so A uses the
platform's default acquisition policy. The controller validates the complete
subject dictionary and benchmark equality, caps matching labels at 31, and puts
compact labeled excerpts in the question. Anonymous benchmark IDs are equality
keys for matching, not a means to identify held-out datasets.

The wrapper in [production.py](../hosted-ble15a/runtime/production.py) validates
the CA bundle, hydrates a hash-bound SQLite corpus with a lock, and coordinates a
scoped spending ledger. The [controller](../hosted-ble15a/runtime/r1api/predictor.py)
receives a typed JSON action and updated public belief per response. The
[Responses client](../hosted-ble15a/runtime/r1api/responses.py) explicitly requests
GPT-6 Luna, standard reasoning mode with medium effort, the default service tier,
an empty native tools list, and a strict JSON schema. Python dispatches tools.
Native encrypted continuation items replay intact. Plaintext hidden reasoning is
not requested or released.

[AuditedDB](../hosted-ble15a/runtime/r1api/db.py) verifies the fixed corpus and mask
for production, applies dynamic target/acquisition exclusions, and filters item
and source variants before reporting evidence. It recomputes affected SQL
aggregates from permitted rows. MiniLM encodes a query locally and ranks normalized
frozen index vectors. Similarity proposes evidence. The model still judges
comparability of the recorded subject, harness and task.

The model-visible R1 prompt describes five steps. A's [Completion policy](../hosted-ble15a/runtime/rescue_policy.json)
actually accepts at most three valid actions inside a 31-second inference window,
uses at most four requests including repair, bounds each HTTP call at 20 seconds,
and requires at least 12 seconds to admit the third call. Initialization occurs
before that inference window. A validated native submit and a previous valid
belief retained after interruption are separate outcomes. If no valid belief
exists, the emergency readout is Beta(4,4) over matching labels, except that the
production financial guard rejects budget-driven fallback. A blocked or rejected
tool cannot quietly supply evidence.

The synthetic walkthrough injects transport and an invented SQLite DB into the
actual controller. It tests JSON validation, request construction, opaque
continuation shape, retrieval and readout behavior. The static production corpus
and hosted credentials are absent. The validated OpenReview restore separately
tested the genuine local encoder and hash-bound corpus with mocked responses.
