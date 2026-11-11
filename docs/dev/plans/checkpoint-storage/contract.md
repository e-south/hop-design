# Storage migration and provenance contract

This is the contract to implement for [compact checkpoints](../checkpoint-storage.md).
It proposes no change to the molecular request, search permissions or evidence
needed to support or exclude a target.

## Three independent identities

- **Object identity** is the SHA-256 of canonical authority bytes. Physical
  compression and object location cannot change it.
- **Creation provenance** records the software that created an authority or
  committed step. A migration cannot replace it with the migrator's version.
- **Executing runtime** identifies the installation performing migration,
  inspection, replay or continued discovery. Record it truthfully, separately
  from the historical creator and physical format.

Preserve existing IDs, duplicate embedded references, selections, request and
record digests. New computations record their actual creator. Do not manufacture
old-version provenance to make a comparison pass. Where a new execution creates
a version-bound authority ID, compare its molecular content and declared
provenance separately rather than normalizing arbitrary IDs away.

## Compatibility requires more than equal bytes

Current bindings occur in several owners:

| Owner | Current behavior to address |
| --- | --- |
| `design/runtime.py` | Producer identity includes every package source file and runtime versions. A storage edit changes that fingerprint. |
| `surveys/index.py` and `admission/checkpoint.py` | Opening requires the stored producer and evaluation limits to equal the invocation. |
| `surveys/navigation/history.py` and `proofs.py` | Exclusion certificates bind a producer and are re-admitted before pruning. |
| `complete/results.py` and `complete/discovery.py` | Complete-result replay regenerates version-bearing provenance and requires canonical equality. |
| `surveys/selection.py` | Old selections bind exact request, record, query and preparation; appending later evaluations is allowed. |
| `surveys/replay/` | Aggregate verification and producer upgrades currently regenerate the committed prefix. |

A storage-only continuation needs a supported compatibility declaration covering
the exact source and target computation contracts, request/limit schemas,
enumeration addresses, proof rules and relevant dependencies. Verify its source
against retained release/source identities. An arbitrary caller-supplied producer
mapping, omitted hash check or monkey patch is not that declaration.

Keep the existing runtime fingerprint. Record accepted creator/runtime changes
once at committed boundaries, without repeating a complete environment document
in every step. Admission must resolve the actual creator of an old proof or
authority; new proofs and steps use the current producer. Preserve historical
canonical bytes and recheck their molecular obligations. Full verification must
understand every supported creator segment before the transition is supported.

The legacy index has one admitted `creator_producer`. The tracked format resolves
the creator of each object, step and cached authority through an admitted ledger.
Each transition seals its prior logical prefix and names the shipped declaration
that admitted the new writer. A version label inside the result being checked
cannot authorize a replay origin.

In particular, test reading and retrieving an older preparation after the package
version changes. Rewriting checkpoint metadata alone does not resolve the
version-bearing complete-result replay path. If the compatible transition is
unavailable, reject continuation and retain the old runtime; do not silently
launch full-history replay or switch scientific permissions.

## Physical store and transactions

Keep legacy reads while introducing one explicitly versioned block layout.
Container hashes protect compressed bytes; original object hashes protect
reconstructed authorities. Unknown versions, missing references, altered bytes,
invalid ranges, overlaps and unexplained block contents fail admission.

Use bounded single-threaded compression, a bounded decompression window and an
8-MiB decoded cache. The measured candidate targets 4-MiB blocks and permits a
larger indivisible object only within the existing 64-MiB object limit. Validate
frame sizes before allocation. A scan must clear stale decoded state, use ordered
cursors and verify every original object hash.

One owner controls each evaluation's transaction. Cache writes may speed later
work but cannot establish coverage. Publishing a committed step requires all its
referenced authorities. Cancellation, a storage limit or an exception cannot
publish half a step, establish exclusion or retain an uncommitted pruning proof
in subsequent execution. Progress follows a successful commit.

## Maintenance operation

Require a stopped source writer and create-only destination. Bind the conversion
to a stable source snapshot, request, limits, source format and creator. Stream
objects in bounded batches. Verify canonical object bytes, metadata, steps,
cache/proof references and continuation state before atomic target publication.

The receipt records source/target file digests, a common logical-content digest,
format versions, creator and migrator identities, object/evaluation counts and
verification performed. Storage conversion establishes equal retained content;
it does not claim to rerun the historical molecular search. Retention thinning
cannot use this receipt to claim lossless conversion.

Bound decoded memory, target size and migration scratch separately. Refuse
inadequate capacity before destructive operations; a stop during conversion
leaves the source authoritative. Detect active writers and refuse to overwrite
an existing target. Keep a tested recovery path for incomplete staging.

## Required tests

- Legacy prefix with success, exclusion proof, unresolved work and a portable selection.
- Cross-version inspection, exact handoff and a matched continuation suffix.
- Unchanged old bytes, IDs, source provenance, coverage, diversity history and cursors.
- Actual executor recorded for new work; incompatible code/dependencies rejected.
- Source mutation, corrupt frames, wrong hashes, missing objects and unknown formats.
- Cancellation or failure before commit, during conversion and at publication.
- Bounded cache eviction and large-object handling, with ordered scans on a large fixture.
- Public API/CLI parity and the installed distribution using synthetic, portable data.
