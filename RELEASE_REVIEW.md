# BLE 1.5-A public release review · v1.5.0-rc.1

The primary artifact is the public-safe companion to scored BLE 1.5-A,
Codabench **#1032237**, with formative Brier ALC **0.1590607804**.
`v1.5.0-rc.1` is the proposed Git tag for the release version
`1.5.0-rc.1` in [CITATION.cff](CITATION.cff).

| Review area | Evidence |
|---|---|
| Scored source | 64 bundled runtime members verified against the reference supplement, including all 35 original Python files. Public configuration has an empty key map and paid inference disabled. |
| Offline notebook | Fresh kernel execution exercises the actual controller with invented fixtures and a mocked transport. The aggregate calculations are checked against released inputs. |
| Published result | The hosted score is formative. The public artifacts provide aggregate arithmetic and source provenance. |
| Reconstruction | Earlier verification with authorized local assets matched 70 of 72 scored ZIP members and passed the official checker, smoke and mocked six-budget retrieval checks. |
| Security | Review covers candidate source, notebook outputs and preview, paper, and reachable Git history. The historical HTTP error tests use synthetic sentinels in mocked failure paths. |
| Links | Release and reconstruction links were checked. Some background links in the frozen MiniLM model card no longer resolve or reject automated requests. Reconstruction uses the separately pinned model reference. |
| Publication | [Candidate file inventory](RELEASE_FILE_INVENTORY.txt) and [approval-gated procedure](docs/publishing.md). |

Six derived data and firewall files require authorized exact copies or verified
deterministic regeneration. This blocks fully independent reproduction of the
exact hosted runtime. The public MiniLM weight is separately pinned and
hash-checked. See [source equivalence](docs/release_manifest.md) and
[data provenance](docs/hosted_data_provenance.md).

The separate historical R1 publication, its review and its original inventory
remain accessible at the
[immutable-by-policy v1.0.0-r1 tag](https://github.com/KarimGhandour/PAIEC-code-submission/tree/v1.0.0-r1).
The root Python distribution `paiec-r1-audited-ble` at `1.0.0` still installs
the historical R1 research modules. Scored A is reconstructed from
`hosted-ble15a/` and has separate release metadata.
