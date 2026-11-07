# Publish the BLE 1.5-A release candidate

The proposed annotated tag is **`v1.5.0-rc.1`**, matching version
`1.5.0-rc.1` in [CITATION.cff](../CITATION.cff). Use the existing
[canonical GitHub repository](https://github.com/KarimGhandour/PAIEC-code-submission)
and publish as a prerelease after explicit maintainer authorization.
The [historical v1.0.0-r1 release](https://github.com/KarimGhandour/PAIEC-code-submission/releases/tag/v1.0.0-r1)
keeps its current tag and commit.

## Preflight

From the candidate checkout, use Python 3.12 with the
[notebook requirements](../requirements-notebook.txt) installed. Run the notebook
with networking disabled as described in [reproduction](reproduction.md).

```sh
git remote get-url origin
git ls-remote origin HEAD 'refs/tags/v1.0.0-r1*' 'refs/tags/v1.5.0-rc.1*'
python scripts/verify_notebook.py
python scripts/verify_results.py
python scripts/validate_release.py --git-history
```

Confirm that `origin` is
`https://github.com/KarimGhandour/PAIEC-code-submission.git`, the historical tag
resolves to `f50814a750aefad56378aa5b0e0e94c076bb7b58`, and the proposed tag
is unused locally and remotely. Stop on unexpected remote history, a tag
conflict, a failed check, or an unexplained difference from the reviewed file list.
Keep the private Codabench ZIP and restricted assets out of the GitHub release.

## Publish after explicit approval

Use the reviewed `codex/hosted-ble15a-release` branch. Stage only the
[candidate inventory](../RELEASE_FILE_INVENTORY.txt). Inspect the staged changes,
then commit and open a pull request.

The whitespace check accepts CRLF line endings and leaves two hash-verified
upstream files with their original whitespace. The release validator checks
their exact bytes.

```sh
git switch codex/hosted-ble15a-release
git -c core.autocrlf=false add --pathspec-from-file=RELEASE_FILE_INVENTORY.txt
git ls-files | LC_ALL=C sort | cmp - RELEASE_FILE_INVENTORY.txt
git -c core.whitespace=cr-at-eol diff --cached --check -- . \
  ':(exclude)hosted-ble15a/runtime/models/minilm/README.md' \
  ':(exclude)hosted-ble15a/runtime/r1api/predictor_common.py'
git diff --cached --stat
git status --short
git commit -m "Prepare scored BLE 1.5-A reproducibility release"
python scripts/validate_release.py --git-history
git push -u origin codex/hosted-ble15a-release
gh pr create --repo KarimGhandour/PAIEC-code-submission --base main --head codex/hosted-ble15a-release --title "Release candidate: scored BLE 1.5-A" --body-file RELEASE_NOTES.md
```

After the pull request merges, verify that the fetched main tree matches the
reviewed commit. If the command fails, stop and review the differences. Proceed
only with a new tag and an unchanged reviewed tree.

```sh
git fetch origin refs/heads/main:refs/remotes/origin/main
git diff --exit-code codex/hosted-ble15a-release origin/main --
git tag -a v1.5.0-rc.1 origin/main -m "Scored BLE 1.5-A reproducibility release candidate"
git push origin refs/tags/v1.5.0-rc.1
gh release create v1.5.0-rc.1 --repo KarimGhandour/PAIEC-code-submission --verify-tag --prerelease --title "BLE 1.5-A reproducibility release candidate" --notes-file RELEASE_NOTES.md
gh release view v1.5.0-rc.1 --repo KarimGhandour/PAIEC-code-submission
```

Cite the full release commit and the new prerelease tag after publication. Git
and GitHub CLI authentication use the maintainer’s existing local configuration.
