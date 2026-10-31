# Frozen results and what the public material verifies

## Audited BLE

Confirmation: 32 questions, 64 matched budget units, four previously used families.
Original subject/family/budget-cell macro Brier:

| Method | Brier | Natural-log NLL |
|---|---:|---:|
| Direct Luna A0 | 0.203883 | 0.581099 |
| R1 initial | 0.172116 | 0.511191 |
| R1 final | 0.153728 | 0.471989 |

Total gain 0.050155 = initial-prompt gain 0.031767 + within-run revision gain 0.018388.
This is observational decomposition, not causal attribution solely to retrieval.
MedAgentBoard regressed. The original cluster intervals, per-family and per-budget
decomposition are in `confirmation_reference.json`. They were measured using
ChatGPT-authenticated Codex CLI, not Responses API or hidden Codabench evaluation.

The completed revealed development panel had A0 0.224650, R1 0.208044 and R2 0.209688.
Both original strict gates failed, including family harm. The continuation/selection
amendment and the fresh-question family-novelty limitation must accompany these claims.

## Ledger extension — rejected

32 questions across eight previously exposed families, matched budgets 0/7. The
deterministic acquisition ledger improves budget-seven mean Brier by 0.014907, but
the family/source-cluster 95% interval is [-0.027450, 0.053648] and some family
regressions exceed the allowed 0.02. The frozen decision is **RETAIN R1**. The ledger
function is included for reproduction but is not imported by the submission predictor.

## Inductive factor model — rejected for strict transfer

694 text/code items, 25,992 outcomes: AlgoTune (154×18), EDIT-Bench (540×43).
Frozen Google EmbeddingGemma 2, 768-dimensional normalized embeddings; rank-16
question projection, source-trained metadata mapping and seven-label MAP adaptation.

| Transfer | Calibrated scalar Brier | Calibrated factor Brier | Gain |
|---|---:|---:|---:|
| AlgoTune→EDIT-Bench | 0.272994 | 0.340420 | -0.067426 |
| EDIT-Bench→AlgoTune | 0.216085 | 0.283372 | -0.067287 |

Only nine shared foundation identities were used; source vocabulary/model fitting
did not use target evaluation outcomes. Original acquisition groups are not
redistributed. Held-item within-family improvement does not override negative
cross-family transfer. This is not a matched improvement over Luna.

## Xhigh effort — rejected

16 historical questions, eight families, matched budgets 0/7; 31 forecasts completed
and one timeout was retained as missing without imputation or retry. Medium Brier
0.254777 versus xhigh 0.262933, paired gain -0.008156, clustered 95% interval
[-0.037405, 0.021776]. Complete-question sensitivity also favors neither promotion.
This is exploratory historical evaluation, not new independent confirmation.
EngDesign, MOE-CAP and SubjectiveQA regressed. No xhigh submission was built.

## Verification boundary

`python scripts/verify_results.py` recalculates point-score aggregation from public
aggregate loss cells and checks reference arithmetic. It cannot validate the raw
item probabilities/outcomes, recompute cluster intervals from lost grouping
information, recreate provider model snapshots, or establish hosted performance.
No per-item outcomes, original protected task text or raw session records are released.
