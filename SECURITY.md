---
doc_id: hop-security
title: HOP Design security and public-data boundary
intent: Define safe inputs, output paths, repository content, and release gates.
audience:
  - maintainers
  - security reviewers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-31
doc_type: reference
---

# HOP Design security and public-data boundary

## Public by construction

Treat every tracked file and built artifact as potentially public. Do not add
private study names, identifiers, selected cohorts, sequences, catalogs,
machine-local paths, credentials, tokens, execution records, or proprietary
constraint profiles. Use short synthetic DNA IUPAC examples only.

Public user guides, API references, architecture decisions, contributor
instructions, and product capability limits belong here. Study plans, manuscript
outlines, investigator decisions, raw observations, and cross-project status
reports belong in the caller's private workspace, not under `docs/dev/`.

The wheel contains the Python package and distribution metadata. The source
distribution also includes public docs, assets, and examples. Excluding a file
from either archive does not make a tracked file private: the repository and
its Git history are public. Content removal from the current tree is not
history erasure. The public-safety and secret checks supplement manual content
review; they cannot determine whether an arbitrary DNA sequence is private.

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
under byte, record-count, and total-nucleotide limits. JSON/YAML specs are read
once through one checked file descriptor and enforce a byte limit before strict
schema dispatch. JSON and YAML reject duplicate mapping keys; YAML also rejects
anchors, aliases, and merge keys. All file readers reject symlinks.
Substrate-space preview and compilation,
symbolic expansion, and design-space planning enforce cardinality before
allocation. Design-set verification recursively inventories member bundles and
rejects unsafe or unexpected files. The offline review embeds no remote
resources. Remote/network resolution stays outside the deterministic core.

Construction source files follow the same bounded regular-file contract. The
reader accepts only `.json`, `.yaml`, and `.yml`, rejects path replacement while
opening, rejects documents larger than one megabyte before decoding, requires a
mapping root, and dispatches only `hop.construction-source/v7`. The source
cannot embed or assert a design authority; compilation loads the separately
supplied design-bundle directory through complete semantic verification.

PCR-bearing sources resolve adapters and endpoint primers only through
strict `derive`, `constrain`, or `fixed` policies. Derived and constrained
primer bindings must remain within invariant non-payload construction sequence.
Caller-supplied handle sequence is explicit input; HOP does not guess a handle
or select one through an unrecorded thermodynamic rule. Direct ssDNA-hairpin
sources reject endpoint-auxiliary policy entirely.

Standalone local-neighborhood results are generated rather than authored and
may contain complete bounded feasibility and rejection evidence. Their portable
loader uses the same descriptor-safe mapping reader with a distinct 64 MiB
limit. Requests remain limited to one megabyte and the public seam rejects
search-node or realization bounds above 100,000. Result loading checks the same
embedded bounds before deterministic replay. Results above their byte envelope
are rejected rather than partially decoded or silently truncated. A declared
sequence-domain partition is limited to 256 parts, binds execution identity,
and cannot be combined with stopping or compatibility semantics that require a
whole-domain conclusion.

Construction-bundle loading rejects unsafe paths, symlinks, incomplete or
extra inventories, modified embedded design artifacts, and checksum-consistent
scientific forgeries through exact semantic replay. Construction authorities
and projection packets use create-only atomic directories and never merge into
an existing destination.

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
