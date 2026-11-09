# HOP Design security and public-data boundary

Keep private data out of tracked files and release artifacts, validate files
before use, and verify the exact distributions before release. The rules below define those
boundaries and the local editor's access controls.

## Local molecular editor

`construction edit-view` binds only to `127.0.0.1`. Mutations require the exact
local Host/Origin and a per-instance token; JSON bodies are bounded and duplicate
keys rejected. Only packaged interface assets and normalized, non-symlink files
inside the newly generated output directory are served. The interface uses no
external scripts or network design services and supports local workstation use only.
Stop it with Ctrl+C when finished.

## Public by construction

Treat every tracked file and built artifact as potentially public. Do not add
private study names, identifiers, selected cohorts, sequences, catalogs,
machine-local paths, credentials, tokens, execution records, or proprietary
constraint profiles. Examples use synthetic DNA IUPAC inputs or explicitly
sourced public reference sequences and enzyme definitions. Public references
must be traceable to the cited source, not copied from private study records.

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

PyPI publication uses the approved trusted publisher for `release.yaml` and the
`pypi` environment. That environment permits only `v*` tags. Publication follows
protected-main ancestry, compatibility and exact-distribution checks. See the
[release process](docs/dev/releasing.md).

## Verification surfaces

The source check, `python scripts/check_public_safety.py`, inventories tracked
and nonignored untracked files through Git. Ignored runtime outputs stay outside
that inventory; tracked files remain in scope even when an ignore rule matches
them. The check requires the repository root, rejects linked paths and files
larger than 2 MB, and scans UTF-8 text for private identifiers and credential
patterns. Only the exact source policy file is exempt because it defines those
patterns. A matching basename elsewhere grants no exemption.

`bash scripts/wheel-smoke [distribution-directory]` independently checks the
actual wheel and source-distribution members before extraction or installation.
Archive scanning uses the same content policy without repository exclusions;
it also rejects unsafe paths, duplicate members, links and special files.
To inspect distributions directly, repeat `--distribution` for each archive:

```bash
# Scan both built distributions before publication.
uv run --locked python scripts/check_public_safety.py \
  --distribution dist/package.whl --distribution dist/package.tar.gz
```

A clean source scan does not attest to a built archive. Ignoring a local output
does not make it safe to package. Non-UTF-8 content and arbitrary DNA sequences
still require manual privacy review; neither automated check authorizes release.

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
mapping root, and dispatches only `hop.construction-source/v8`. The source
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

Foldback sequence-space requests and results use the same one-megabyte and
64 MiB descriptor-safe input limits. Strict embedded execution bounds apply
before rediscovery; exact payload expansion is preflighted against the case
limit. Canonical sequence decisions receive structural and cardinality checks,
then the entire result is recomputed before a verified receipt is returned.
Membership changes or omitted cases remain invalid even when their totals and
content identities are recomputed consistently.

Construction-bundle loading rejects unsafe paths, symlinks, incomplete or
extra inventories, and modified embedded design artifacts. It reruns the
recorded derivation to reject molecular changes even when checksums have been
recalculated to match the changed files. Construction authorities
and projection packets use create-only atomic directories and never merge into
an existing destination.

## Release gate

Before any GitHub release, run `bash ./scripts/agent-verify`, inspect wheel and
sdist contents, review dependency and secret scans, and verify the wheel in a
clean environment. The release workflow smoke-tests the exact distributions it
attaches to the GitHub release. Only the attachment job receives
`contents: write`. Within that release workflow, only the PyPI job receives
`id-token: write`. It has no checkout,
uses the scoped trusted publisher and checks the verified distribution bytes
before upload.

Report vulnerabilities with a private GitHub Security Advisory. Do not include
sensitive sequences or credentials in public issues. PyPI publication requires
an explicit trusted-publisher decision; no long-lived publishing credential
belongs in repository or Actions secrets.
