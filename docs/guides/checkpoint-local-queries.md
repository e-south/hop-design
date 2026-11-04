---
doc_id: hop-checkpoint-local-queries
title: Checkpoint independent local queries
intent: Persist and resume a finite collection without changing individual request authorities.
audience: [Python users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-06
doc_type: how-to
journey: [discover, verify]
---

# Checkpoint independent local queries

Use this optional batching path after authoring independent local queries.
It is separate from [compiling one complete construction](compile-construction.md).

## Run and resume the collection

For a finite collection of strict local-neighborhood requests, use the public
batch operation. Each request retains its own geometry, enzyme domain, search
limits, status, canonical result bytes, and realization identities.

```python
import hop_design.construction as construction

sources = ["foldback-top.yaml", "foldback-bottom.yaml"]
partial = construction.discover_local_neighborhoods(
    sources,
    "local-results",
    max_new_requests=1,
)
finished = construction.discover_local_neighborhoods(
    sources,
    "local-results",
    resume=True,
)
for result in finished.iter_results():
    print(result.completion, result.feasibility, result.result_id)
```

The first call is create-only. Resume requires the same normalized ordered
requests, package-content identity, and recorded Python/dependency versions.
Saved results pass full molecular replay before more queries execute. A changed
producer or corrupted authority fails; it is not silently recomputed or replaced.
Move the whole directory to transfer it. Source filenames and destination paths
are not part of its identity.

The directory contains a normalized `plan.json`, compressed canonical results
under `batches/`, and `complete.json` only after every request has returned.
Each immutable batch contains `results.jsonl.gz` and `inventory.json`. Batch
size may change on resume without rewriting completed files or changing result
identity. A `.pending-` directory left by a killed process is unpublished staging,
not an authority; resumption leaves it untouched and executes the unfinished
queries again.

Limits are 4,096 requests, 1–256 requests per write batch, a 64-MiB normalized
plan, and 64 MiB of decompressed canonical results per batch. A batch flushes
at either its byte or request limit. Each local request still uses the existing
bounded in-memory discovery engine. Checkpointing occurs **between requests**,
not inside one large search. Resumption avoids rediscovering unfinished work
from the beginning of the collection, but replay of saved results still costs
computation. Concurrent writers must use separate destinations; publication
refuses to overwrite another writer's batch.

`finished` means every request returned, including requests that were truncated
or stopped at a quota. It is not a combined molecular completeness claim.
Repeated or overlapping requests are not deduplicated and their realization
counts must not be summed as unique molecules without a separate comparison.
