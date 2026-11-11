# Compact discovery checkpoint storage

Keep long discovery searches affordable by sharing repeated bytes within each
evaluation and validating stored objects in a streaming scan. This is an
implementation plan. The released checkpoint format and commands are unchanged.

## Ownership

HOP owns record storage, integrity, migration, continuation, inspection and exact
retrieval through its public API and CLI. Applications own molecular requests,
search allocation, execution budgets, host deployment and publication selection.
Application benchmarks may motivate a change; their sequences, directories and
controllers do not enter HOP.

Promote the reusable mechanism with synthetic fixtures. Keep the experiment
history and application measurements with their authors. A reproduction package
pins the released HOP version and declares its data and workflow inputs.

## Preserve the scientific records

The first increment is lossless: retain all canonical object bytes, preparation
identities, evaluation addresses, coverage, proof bodies and continuation state.
Physical storage, creator provenance and the executing installation are separate
facts. The [storage contract](checkpoint-storage/contract.md) defines their
invariants and the compatibility checks needed before continuation.

Compact failed-attempt records, cache eviction and incremental continuation state
are later increments. They need their own contracts; none is required to share
repeated bytes in the existing records.

## Implementation order

1. **Prove cross-version use first.** Build a small legacy fixture with a complete
   preparation, a committed exclusion proof and pending work. Test inspection,
   selected retrieval and a bounded continuation under the candidate installation.
   Preserve creation provenance while recording the actual executor. Resolve
   producer, proof and saved-bundle replay bindings before a large migration.
2. **Introduce the physical store.** Keep `SurveyIndex` as the facade. Separate
   legacy decoding, bounded block encoding, integrity scanning and migration
   publication below `surveys/storage/`. Share transaction ownership rather than
   duplicating index logic. Add only the interfaces used by both layouts.
3. **Share each evaluation's writes.** Encode new objects in bounded blocks,
   retain their original SHA-256 addresses and atomically publish the completed
   step with its references. Flush bounded buffers into the transaction; never
   buffer a whole discovery call. Rollback must also invalidate uncommitted
   decoded/cache/proof state.
4. **Add explicit storage migration.** Expose one maintenance operation through
   `hop_design.construction` and the existing survey CLI. Use a create-only
   destination, writer exclusion, bounded work, progress, cancellation and a
   content-verification receipt. Report storage conversion separately from
   molecular replay. Do not add arbitrary producer overrides to resume.
5. **Qualify one settled candidate.** Exercise both layouts, crash recovery,
   unchanged old selections, proof reuse, compatible continuation and exact
   material handoff. Run the appropriate source/distribution gate once the
   implementation settles. A new runtime dependency also needs installation
   and supported-Python qualification before release.
6. **Release, then let applications adopt it.** Publish a pinned package with
   public instructions for inspection, migration and recovery. Consumers stage
   one stopped checkpoint, verify continuation and retrieval, then migrate within
   their disk budget. A storage release does not select a scientific edition.

## Reader and writer design

The block store owns compression, content checks, object ranges and a bounded
decoded cache. It receives bytes and digests; it knows nothing about enzymes,
stems or paper-specific diversity rules. Keep the codec dependency and native
requirements in the package environment rather than a user's application script.

The integrity scan reads block and object-range cursors in order, validates every
container and original object hash, and checks complete non-overlapping ranges.
New stores index that order. Point reads use the same decoder and integrity
rules. Both paths operate within a caller-owned read snapshot.

Inspection reports encoding, stored bytes, object and cache counts, original
producer and current executor where applicable. Progress distinguishes bytes
converted from evaluated requests. Normal opening performs integrity admission;
the explicit scientific verification operation retains its molecular replay
meaning.

## Acceptance boundary

Ready means a legacy checkpoint can be migrated, inspected, continued and
retrieved through the installed public tool with its historical records intact.
It also means interrupted migration leaves a recoverable source and no published
partial target, and unknown formats or incompatible producers fail clearly.

Measure storage, full admission, point reads, continuation and peak migration
disk separately. Compare the same scientific requests and budgets. A faster
integrity scan alone does not establish faster discovery.

See [verification boundaries](../performance/verification.md),
[existing checkpoint semantics](../../architecture/decisions/0052-resumable-interface-surveys/checkpoints-and-inspection.md)
and the [construction module map](../construction-map.md).
