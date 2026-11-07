# Source equivalence | hosted-ble15a

The source of this release candidate is the already validated 579,597-byte
OpenReview supplement, SHA-256 08ab46ce10b504b0b9458c07eaf11f3194401830b618c5072140ad1fc2947537.
It identifies the frozen local scored A archive, 695,451,321 bytes, SHA-256
90a6a22560328e4ff5ec3f86375dbf567aecf802d2632fe6829878b339be7c3c. The saved
authenticated record connects the selected artifact to #1032237. No fresh
server-container hash is claimed.

| Class | Disposition |
|---|---|
| Unchanged bundled | 63 original members, including all 35 Python files |
| Sanitized | submission_config.json removes the key and disables paid inference |
| External, hash-bound | Seven original members, of which one is public MiniLM and six are derived data or firewall files |
| Regenerated on restore | PACKAGE_HASHES.json reflects the sanitized config and restored members |

The [per-member manifest](../hosted-ble15a/ARTIFACT_MANIFEST.json) maps every
packaged or external member to a SHA-256 and exact size. With authorized local
assets the earlier full reconstruction matched 70/72 member contents and passed
the official ZIP checker, smoke and genuine local retrieval under mocked
Responses at all six budgets. The outer ZIP bytes differ. The frozen source
configuration remains a safe offline default.

This candidate keeps the public research R1 files and tag lineage from commit
f50814a750aefad56378aa5b0e0e94c076bb7b58. Public notebook helpers, anonymized
aggregate CSVs and figures live outside the scored runtime tree. They are not
part of the reconstructed submission. The frozen artifact itself was not changed.
