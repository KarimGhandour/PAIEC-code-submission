# Public release review

Status: locally prepared; **not published or pushed**. GitHub authentication was
unavailable. Public release still requires explicit maintainer authorization.

| Check | Result |
|---|---|
| Exact selected R1 source | 34 whitelisted members match approved compact ZIP hashes |
| Frozen prompt/tool schema hashes | Recorded and checked against unchanged source |
| Offline suite | 56 tests: 52 passed, 4 explicit private-record skips |
| Root predict interface | Mocked R1 forecast at all six acquisition budgets |
| Retrieval | All eight operations on invented SQLite/FTS/Parquet fixtures; exclusion and trace checks pass |
| Transport | Reasoning-state continuity, bounded schema repair, clipping, failure and spending controls pass |
| Factor method | Synthetic numerical regressions and authorized-array CLI toy smoke pass; no pretrained encoder used |
| Clean source/interpreter | Temporary independent source checkout and new virtual environment; pinned dependencies reused locally offline |
| Editable installation | Passed with no dependency downloads |
| Result arithmetic | Historical confirmation, ledger and xhigh aggregate point estimates, factor-reference gain arithmetic reproduced |
| Source-data command | Pinned official inventory dry run passes; no files downloaded |
| Configuration | Empty key, paid inference disabled and owner-only file creation checked in temporary checkout |
| Secret/restricted artifact review | Whitelist export; heuristic/structural file scan, exact-known-credential comparison, staged inventory and initial Git-history scan |
| Licensing | MIT code; original upstream notice retained; no dataset/model weights redistributed |
| Original submissions/manuscript | Not modified; no new uploads or paid inference |

Four inherited tests are explicit skips: archived private action/evidence replay,
real historical SQL packet parity, original native encrypted-state replay, and the
original private static-cache fixture. Public synthetic tests test mechanisms;
they are not claimed to replace those historical evidence validations.

The new temporary environment reused local pinned site packages. It was **not** a
fresh online reinstall of every dependency or a hosted Linux test. Core source,
tests and documented offline commands work outside the original research directory.
No public command depends on an absolute workstation path.

The released cell summaries verify aggregate arithmetic, not raw per-item losses,
protected outcomes, original bootstrap resampling or historical provider snapshots.
Exact corpus reconstruction and historical forecast regeneration require separately
authorized artifacts. No API Brier of 0.153728 or hidden score is claimed.

Security review intentionally omits private configuration, credential-bearing ZIPs,
raw/derived data, individual outcomes and probabilities, model weights, session/account
metadata and native encrypted reasoning logs. The scanner reports rule/path names
only. Known credentials are compared privately without printing their values. No
heuristic scanner proves absence of arbitrary unknown secrets; whitelist/manual
review and a clean one-commit history supplement the automated checks.

The exact release file list is `RELEASE_FILE_INVENTORY.txt`; source/content sizes
are summarized in `artifacts/manifests/release_checks.json`. The final commit ID is
reported separately rather than recursively embedded in its own contents. The
publication commands and proposed immutable-by-policy tag `v1.0.0-r1` are in
`docs/publishing.md`. Do not execute them before explicit release authorization.
