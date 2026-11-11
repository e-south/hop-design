# Checkpoint storage and migration

New surveys store immutable object bytes in shared Zstandard blocks. Existing
zlib checkpoints remain readable under their original producer. Object hashes,
preparation IDs, selections and scientific records do not depend on compression.

`construction survey inspect` reports the format, encoding, allocated and encoded
bytes, object count and creator count alongside coverage. Allocated bytes include
SQLite pages; encoded bytes count compressed payloads.

## Convert a stopped checkpoint

Stop its writer first. Migration preserves the source and creates a new directory:

```bash
# Convert saved content; no historical constraint search is rerun.
hop-design construction survey migrate request.json \
  --index old.sqlite --out compact \
  --max-checkpoint-bytes 1073741824 --minimum-free-bytes 1073741824
# Progress appears on stderr; stdout contains the conversion receipt.
```

The directory contains `survey.sqlite`, the canonical `request.json` and
`migration.json`. The receipt binds source and target file hashes, a common
logical-content digest, formats, producers, object/evaluation counts and coverage.
Every original object hash and saved reference is checked before publication.

Keep the original checkpoint and runtime until retrieval and a short continuation
have passed. Use the original request and evaluation limits with `--resume`,
changing the index path to `compact/survey.sqlite`. The conversion preserves old
selections; appended work records its actual producer.

## Producer compatibility

Normal resume requires the checkpoint's current writer to match the installation.
Migration can change that writer only when HOP ships a compatibility declaration
for the exact source package and target code. Runtime inputs must also match.
There is no force flag or caller-supplied compatibility policy.

Creator history is recorded once per transition. Existing objects, records and
proofs retain their original creator; new evaluations use the current runtime.
Full `survey verify` understands this history and recomputes the saved molecular
work. Migration checks equal retained content; it does not perform that search.

`survey upgrade` remains a separate, explicit full-history replay operation for
single-creator checkpoints. It can take as long as the saved search. Use migration
for a supported storage transition.

## Bounds and recovery

Compression is single-threaded. Blocks target 4 MiB; an indivisible object may
reach the existing 64-MiB object limit. Decoded block caching is limited to 8 MiB.
One evaluation and its referenced objects commit together, before progress is
reported. Cancellation, failure or a storage limit rolls back that evaluation.

Migration reserves space for the target capacity, 128 MiB of journal allowance
and the requested free-space reserve. It refuses active writers, journals,
unknown formats, incompatible producers and existing destinations. Handled
interruptions remove staging. After a power loss, the original remains the
authority; inspect any `.DESTINATION.*` staging directory before removing it.

See [execution and coverage](execution-and-coverage.md) for search scope and
[the storage contract](../../dev/plans/checkpoint-storage/contract.md) for
implementation invariants.
