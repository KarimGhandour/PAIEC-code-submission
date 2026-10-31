# Canonical GitHub publication

Repository: https://github.com/KarimGhandour/PAIEC-code-submission

The repository already exists. **Do not create another repository.** The local
directory and Python distribution can retain the name `paiec-r1-audited-ble`.
The maintainer explicitly authorized publication of this vetted source and release;
that authorization does not extend to inference or competition submissions.

Before publishing, check remote refs and preserve unrelated work. Never force-push.
From the local repository, with working existing Git/GitHub credentials:

```sh
git remote get-url origin
git ls-remote origin
python scripts/check_source.py
python -m unittest discover -s tests -v
python scripts/scan_release.py --git
git push -u origin main
git tag -a v1.0.0-r1 -m "Frozen R1 Medium source and public reproducibility release"
git push origin v1.0.0-r1
gh release create v1.0.0-r1 --repo KarimGhandour/PAIEC-code-submission --verify-tag --title "R1 Medium reproducibility release" --notes-file RELEASE_NOTES.md
```

`origin` must equal `https://github.com/KarimGhandour/PAIEC-code-submission.git`.
If the local tag already exists, verify its commit instead of recreating or moving
it. Stop on unexpected remote history, tag conflicts or security findings.
Do not attach private Codabench ZIPs or restricted assets to the GitHub release.

Authentication is handled locally by Git/gh. Never put credentials in source or
command arguments. A failed credential does not establish that the repository
owner's account is unavailable; diagnose the credential identity separately.

Citation links:

- Repository: https://github.com/KarimGhandour/PAIEC-code-submission
- Release: https://github.com/KarimGhandour/PAIEC-code-submission/releases/tag/v1.0.0-r1
- Frozen commit: `https://github.com/KarimGhandour/PAIEC-code-submission/tree/FULL_COMMIT_SHA`

An annotated tag remains technically mutable. Treat `v1.0.0-r1` as immutable by
policy, retain its full commit SHA, and cite an archival DOI only if one is later
actually minted. No DOI, institutional affiliation or contact address is invented.
