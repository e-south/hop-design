# Release HOP

A release publishes the same verified wheel and source archive to GitHub and
PyPI. The workflow checks the package version, protected-main ancestry,
Python compatibility and clean-install behavior before publication.

## First PyPI setup

Create a pending [Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
in the owner's PyPI account with these values.

| Setting | Value |
| --- | --- |
| Project | `hop-design` |
| GitHub owner | `e-south` |
| Repository | `hop-design` |
| Workflow | `release.yaml` |
| Environment | `pypi` |

The matching GitHub `pypi` environment permits only `v*` release tags. The PyPI
job receives a short-lived OIDC identity and verified files, with no checkout or
stored API token. Build and GitHub publication jobs cannot publish to PyPI.

## Publish a version

1. Merge the version and documentation through a green pull request.
2. Tag that exact main commit. This starts the release workflow.
3. Confirm both the GitHub release and PyPI files.
4. Test `uv tool install "hop-design==0.1.0a9"` outside the checkout. Confirm the
   installed version and the Python import before announcing availability.

```bash
# Tag a version only after its protected-main checks pass.
git switch main
git pull --ff-only
git tag v0.1.0a9
git push origin v0.1.0a9

# Watch publication and inspect the uploaded files.
gh run list --workflow release.yaml --limit 1
gh release view v0.1.0a9
```

The release build runs extended qualification on the exact distributions and
records their checksums. Python 3.12/3.13 compatibility runs alongside it. The
GitHub job attaches those files before publishing; the PyPI job downloads the
same files and verifies their checksums again before upload.

## Recover a failed publication

Inspect the failed stage before retrying. A GitHub rerun refuses to replace an
existing release or incomplete draft. Resume a failed PyPI job with **Re-run
failed jobs** after correcting its setup, preserving the already verified files.
PyPI does not permit replacement of uploaded distributions. Correct a bad package
with a new version; retain the original release and its provenance.

Keep exploratory inputs and downstream migration policy outside this repository.
