---
doc_id: hop-releasing
title: Release process
intent: Separate GitHub artifact creation, PyPI authorization, and downstream adoption.
audience:
  - maintainers
  - release operators
owner: HOP Design maintainers
status: active
last_verified: 2026-11-04
doc_type: how-to
journey:
  - maintain
---

# Release process

HOP has two distribution gates. A public GitHub repository provides source,
pull-request review, tags, releases, and downloadable wheel/sdist artifacts.
PyPI is a separate package index and authorization boundary. GitHub publication
does not imply PyPI publication.

## GitHub release artifacts

1. Merge a narrow version change through a green pull request.
2. Confirm the full Python 3.12 gate (`bash ./scripts/agent-verify`),
   `twine check`, dependency review, CodeQL, and public-safety checks.
3. Push the exact protected-main commit as tag `v<project-version>`. The tag
   starts the release workflow; do not create an empty Release first.
4. The workflow verifies tag/version and
   main ancestry, builds wheel and sdist with `uv build --no-sources`, performs
   extended clean-install qualification (`scripts/wheel-smoke dist`) on those exact files, records their SHA-256 checksums,
   and runs Python 3.13/3.14 compatibility at the tagged commit. Publication
   waits for both jobs, then creates the versioned GitHub Release with the
   distributions and `SHA256SUMS` in one publish operation. A one-day Actions artifact only
   transfers the verified bytes between the read-only build job and the narrowly
   privileged publish job.

The build job allows thirty minutes for the extended gate; its last completed
distribution stage took approximately eighteen minutes. It has read-only contents
permission. Only the publish job has
`contents: write`, and it receives no checkout. The GitHub CLI creates a draft,
uploads the verified assets, and publishes only after upload succeeds. No job
receives an OIDC token or can publish to PyPI. A rerun refuses to replace an
existing release or incomplete draft. Inspect and remove an incomplete draft
explicitly before retrying the same tag.

For Python-version-sensitive changes, request earlier compatibility evidence with
`gh workflow run python-compatibility.yaml --ref <candidate-ref>`. This is optional
for ordinary changes; release compatibility is already mandatory and need not be
run manually as a routine prerequisite.

## Future PyPI gate

PyPI remains disabled while `Private :: Do Not Upload` appears in package
classifiers. Opening the gate requires a separate pull request that records the
package name, production PyPI project, trusted publisher, protected `pypi`
environment, rollback owner, and first successful hosted build evidence.
Trusted Publishing should use short-lived OIDC credentials; no long-lived PyPI
token belongs in GitHub secrets.

Downstream migration may use a versioned GitHub release artifact before PyPI
exists. Editable sibling paths are suitable only for local probes.
