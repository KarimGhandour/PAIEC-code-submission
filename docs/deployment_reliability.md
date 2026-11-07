# Reliability and runtime evidence

A valid native submit, a valid prior belief retained, and an emergency Beta
probability are distinct. An invalid reply is rejected, and the controller may
repair once or return a prior valid belief. Budget exhaustion can fail closed.
A batch-fatal error prevents normal completion. A confirmed total-runtime
timeout requires an explicit diagnostic or trustworthy timing evidence.

The A.2 local stress campaign used 3,000 mocked forecasts, 200 injected faults
and 9,020 mock API requests. It returned 2,820 native submits and 180 earlier
beliefs, with zero emergency readouts. This was engineering coverage. It does
not estimate a hosted error rate or probability of meeting the deadline.
Hosted A.2 #1033843 failed with PAIEC-UNKNOWN-001. Cause and timeout status
remain unverified.

Cold start materializes the SQLite corpus and loads a local encoder when needed.
Within a forecast, the request and validated continuation are sequential. Across
forecasts, local runner replay filled configured 4/8/16 slots. Hosted allocation,
cross-scope overlap, effective provider limits, and counted runtime are not
observable from the public score or the scope-local telemetry code. The eight-hour
rule remains applicable. The measured local times do not establish compliance.

If n independent jobs each fail with constant probability q, the illustrative
risk of at least one failure is 1 − (1 − q)^n. Shared assets and throttling can
create correlated failures, and many interruptions are recoverable. The notebook
uses the formula as a teaching example with hypothetical q values.
