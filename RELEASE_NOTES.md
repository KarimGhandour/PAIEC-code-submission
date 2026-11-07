# BLE 1.5-A release candidate · v1.5.0-rc.1

This release candidate accompanies scored Codabench submission **#1032237**,
which achieved **0.1590607804 formative Brier ALC** across nine
subject–benchmark groups and six acquisition budgets.

It includes the scored Standard/Medium runtime source, with private configuration
sanitized and paid inference disabled, plus the executable offline notebook,
an HTML preview, aggregate results and reconstruction instructions.

The frozen scored ZIP was 695,451,321 bytes with SHA-256
`90a6a22560328e4ff5ec3f86375dbf567aecf802d2632fe6829878b339be7c3c`.
Reconstructing the exact runtime inputs requires a pinned public MiniLM weight
and six derived data and firewall files. Independent reproduction of the exact
hosted runtime remains blocked without authorized copies of those six files or a
verified byte-matching regeneration process.

The earlier R1 Medium code and public confirmation remain available under the
[historical v1.0.0-r1 release](https://github.com/KarimGhandour/PAIEC-code-submission/releases/tag/v1.0.0-r1).
Its 0.153728 historical public Brier and the formative BLE 1.5-A Brier ALC use
different samples and estimands.

- [BLE 1.5-A Explained](notebooks/01_BLE_1_5A_Explained.ipynb)
- [Source equivalence](docs/release_manifest.md) and [reproduction](docs/reproduction.md)
- [Release review](RELEASE_REVIEW.md) and [publishing procedure](docs/publishing.md)
