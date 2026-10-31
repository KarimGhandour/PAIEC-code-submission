# Publication workflow — explicit authorization required

No remote repository has been created and no code has been pushed. GitHub
authentication was unavailable during preparation. Do not infer publication from
a local commit, version field, citation metadata or proposed URL.

Proposed repository: `paiec-r1-audited-ble`.
Description: `Frozen PAIEC GPT-6 Luna R1 audited BLE source, offline tests and reproducibility analyses.`
Recommended annotated release tag: `v1.0.0-r1`.

After the maintainer authorizes public release, authenticate locally using the
normal GitHub CLI flow. Never provide tokens in chat or source. From this repository:

```sh
gh auth login
OWNER=$(gh api user --jq .login)
gh repo create "$OWNER/paiec-r1-audited-ble" --public --source=. --remote=origin --description "Frozen PAIEC GPT-6 Luna R1 audited BLE source, offline tests and reproducibility analyses"
git push -u origin main
git tag -a v1.0.0-r1 -m "Frozen R1 Medium source and public reproducibility release"
git push origin v1.0.0-r1
gh release create v1.0.0-r1 --verify-tag --title "R1 Medium reproducibility release" --notes-file RELEASE_NOTES.md
```

These are prepared commands, **not authorization to execute them**. Before pushing,
run `python scripts/scan_release.py --git` and inspect `git ls-files`. The current
initial commit uses the author's supplied name with an empty email rather than
inventing or exposing a contact address. Configure a verified privacy-preserving
GitHub identity before future commits if desired.

After creation, add the verified `repository-code` URL to CITATION.cff in a reviewed
metadata-only commit if desired. No account name, public URL, DOI or affiliation
has been invented in this repository.

OpenReview URL formats, after actual publication:

- Release: `https://github.com/OWNER/paiec-r1-audited-ble/releases/tag/v1.0.0-r1`
- Frozen commit: `https://github.com/OWNER/paiec-r1-audited-ble/tree/FULL_COMMIT_SHA`

A Git tag is technically mutable. Treat the release tag as immutable by policy,
retain its exact commit SHA, and prefer an archival DOI if one is later actually
minted. No DOI is claimed or created by this workflow.
