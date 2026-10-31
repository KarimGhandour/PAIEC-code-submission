# Method and historical experimental design

R1 forecasts binary success for one visible subject configuration and task. It
receives permitted task context and a subject-matched acquired-label snapshot.
Initial belief is Luna's first declared probability before retrieval observations;
final belief is its validated submission. Every action has a structured belief.

The eight tools are `find_model`, `search_benchmarks`, `get_benchmark`, `get_scores`,
`search_items`, `get_item`, `get_trace`, and `semantic_search_items`. They execute in
trusted Python, not in model-controlled shell/SQL. Query text and retrieved task text
are untrusted. SQL parameter binding, frozen exclusions, source-key propagation,
exact/near-duplicate blocking and permission quarantines restrict evidence.
Semantic similarity is not historical success probability, and an unrelated
benchmark rate is not a calibrated target-item probability.

R1 uses the original frozen BLE prompt; R2 appends the released fixed evidence
policy and adds relevance/compatibility evidence. R2 is a historical comparison,
not the selected deployment. A0 is the frozen direct-Luna control, not an empirical
mean. Historical A0 instructions and context were not a fresh API ablation, so the
A0→R1 contrast combines prompt and retrieval-loop effects.

Development used 16 revealed questions from KernelBench, CellVerse, MMLU-Pro and
StatQA at 0/7. Original strict development gates failed for both R1 and R2. A
documented transport/continuation amendment allowed a completed mixed-signal study
to proceed unless predefined severe futility held; R1 was chosen under that amended
rule (within 0.002 of R2 favored R1). Do not retrospectively label the original gate
as passed. Released development diagnostics preserve this distinction.

Confirmation used 32 fresh source groups across LexEval, LiveAoPSBench, MathArena
and MedAgentBoard, with matched 0/7 forecasts and no post-confirmation retuning.
The families were already represented in prior research; this is fresh-question
confirmation, not four entirely unseen families. Prediction freeze preceded
confirmation outcome access. The original isolation was macOS Seatbelt with a
trusted external tool coordinator, not merely separate working directories.

Original confirmation aggregation is mean Brier/NLL within each
`(family,subject,budget)` cell followed by an equal mean over cells. It is not an
equal-family macro when family subject counts differ. Ledger/xhigh explicitly use
equal families, with equal subject/budget cells within family. Both exact scorer
implementations are retained, with a test showing their difference on an unbalanced
panel. Natural-log NLL is secondary; Brier and NLL are not interchangeable.

Cluster intervals resample families then original-source groups inside subject
strata, keeping matched methods, repeated trials and budgets together. The bootstrap
uses seed 20261029 and 2000 draws. Public aggregate cells cannot reconstruct this
sampling hierarchy: the implementation is released, original confidence intervals
are reference records, and full numerical recomputation requires authorized records.

Six-budget Brier ALC is implemented separately with weights
0.1/0.2/0.2/0.2/0.2/0.1 at 0/1/3/7/15/31. The two-budget research panels do not
establish an official six-budget ALC or a competition hidden-test result.
