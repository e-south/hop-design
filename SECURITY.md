---
doc_id: hop-security
title: HOP Design security and public-data boundary
intent: Define safe inputs, output paths, repository content, and release gates.
audience:
  - maintainers
  - security reviewers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-27
doc_type: reference
---

# HOP Design security and public-data boundary

## Public by construction

Treat every tracked file and built artifact as potentially public. Do not add
private study names, identifiers, selected cohorts, sequences, catalogs,
machine-local paths, credentials, tokens, execution records, or proprietary
constraint profiles. Use short synthetic DNA IUPAC examples only.

The distribution carries `Private :: Do Not Upload` as an accidental PyPI
publication brake. A public GitHub repository and a PyPI package are separate
distribution channels. Removing the brake or adding a publishing identity
requires a separate release change.

## Untrusted inputs and paths

Pydantic boundaries reject unknown fields and unsafe alphabets before planning.
Bundle artifact paths must be normalized relative POSIX paths with no parent
traversal. Verification rejects symlinks and unmanifested files. Bundle writing
refuses any pre-existing target instead of merging or overwriting content.

FASTA and CSV readers create the same strict payload records as inline callers
under byte, record-count, and total-nucleotide limits. JSON/YAML specs enforce a
byte limit; YAML uses safe deserialization followed by strict schema dispatch.
All file readers reject symlinks. Substrate-space preview and compilation,
symbolic expansion, and design-space planning enforce cardinality before
allocation. Design-set verification recursively inventories member bundles and
rejects unsafe or unexpected files. The offline review embeds no remote
resources. Remote/network resolution stays outside the deterministic core.

## Release gate

Before any GitHub release, run `bash ./scripts/agent-verify`, inspect wheel and
sdist contents, review dependency and secret scans, and verify the wheel in a
clean environment. The release workflow smoke-tests the exact distributions it
attaches to the GitHub release. Only the attachment job receives
`contents: write`; no job receives OIDC permission or can publish to PyPI.

Report vulnerabilities with a private GitHub Security Advisory. Do not include
sensitive sequences or credentials in public issues. PyPI publication requires
an explicit trusted-publisher decision; no long-lived publishing credential
belongs in repository or Actions secrets.
