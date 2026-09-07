---
doc_id: retained-overhead-construction-inventory
title: Retained-overhead construction implementation inventory
intent: Locate construction responsibilities, remaining capabilities, and measured allocation costs.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-09-07
doc_type: explanation
journey:
  - maintain
---

# Retained-overhead construction implementation inventory

This public inventory locates construction behavior, incomplete capabilities,
and reproducible performance measurements. Scientific evidence and publication
planning belong to the consuming system.

## Reusable implementation

- `models.payload`, construction payload references, and source maps already preserve exact and patterned payload identity without permitting route code to edit the payload.
- Characterized enzyme records already carry strict recognition, strand, cleavage, substrate-state, terminal-state, and provenance facts.
- Foldback and basal kernels already enumerate exact sequence placements and return explicit molecular failures.
- Foldback and basal realization records already preserve enzyme bindings, literal pairing, retained and released sequence, bonds, material roles, and deterministic identities.
- Complete construction already composes selected verified local authorities, derives source and auxiliary materials, replays endpoint-specific molecular transitions, binds optional source-partition evidence, and verifies endpoint encodings.
- File-oriented public receipts, canonical JSON, create-only publication, replay verification, and typed projections provide the correct authority boundary.

## Implemented boundaries

- Foldback search is ordered by absolute retained non-payload overhead.
- Basal search uses primitive pairing and future-release obligations rather than named
  profiles.
- Source-partition authorities certify both complete source strands across the caller's
  finite inclusive maximum-fragment ladder.
- Selected complete routes bind exact source preparation, source partition, molecular
  chronology, and endpoint evidence.
- Public projections expose local overhead, basal enzyme-action minima, exact source
  partitions, route navigation, and selected route trajectories.
- Foldback and basal traversal yield exact geometry/strand/payload/program work units
  without materializing the payload cross product. Family discovery retains ownership
  of evaluation limits, existence stopping, coverage, and result assembly.
- Public collection execution checkpoints independent local queries in bounded,
  immutable batches. Requests, producer bytes, and runtime versions bind resumption;
  saved results require molecular replay. Batch sizing leaves result identities intact.

## Remaining product requirements

- Each local query still returns an in-memory result. Public checkpoints persist between
  independent queries; they do not yet stream realizations or resume within one query.
  Internal lazy traversal supplies finer work-unit boundaries, but persistence of that
  partial coverage remains unimplemented. A completed collection does not establish
  exhaustive coverage for a truncated query.
- Source-partition discovery evaluates enzyme programs on one supplied exact source
  duplex. Its full-span certificate does not establish bounded scaffold-sequence or
  context-extension solving around local and primer obligations. That completion search
  remains separate implementation work.
- The post-release construction changes require a distinct package version and immutable
  producer cutoff before downstream formal execution. A wheel bearing the published
  version number is insufficient to distinguish these semantics.

## Downstream work

- Client studies own finite analysis requests, independent execution, figure rendering,
  and scientific review. Their run status belongs in their own records.
- Manuscript systems own evidence admission and publication claims.
- Physical recovery and sequence-confirmation evidence remain outside HOP.

## Foldback allocation measurement

The first-solution memory regression uses a 12-nt loop, a 3-bp arm, zero junction
offset, exact payload `GACT`, and the synthetic `ACATTT` nick-action fixture in
`tests/contract/test_foldback_construction_discovery.py`. On Python 3.12.11,
three `tracemalloc` measurements of the first solution were:

| Enumeration | Peak traced allocation (bytes) | Elapsed time (seconds) |
| --- | --- | --- |
| Buffered nested Cartesian product | 37,933,278; 37,661,870; 37,661,070 | 0.8034; 0.7657; 0.7769 |
| Positional Cartesian product | 15,514; 15,442; 14,642 | 0.00126; 0.00113; 0.00145 |

The allocation hotspot was materialization of all loop assignments before the
first candidate was requested. Positional enumeration preserves arm-major,
loop-minor order while holding only the per-position domains and current
assignment. These measurements concern first-solution allocation, not total
search throughput or saved-authority verification. Both the first sequence
digest and a complete small-domain sequence-order oracle are unchanged.

Run the regression with:

```bash
uv run pytest -q tests/contract/test_foldback_construction_discovery.py
```

## Local execution allocation measurement

`scripts/benchmarks/local_discovery.py` compares retained query receipts,
checkpointed execution, and full resume replay using identical requests and
canonical bytes. Run it with the public `examples/foldback-local-partition.yaml`
fixture. On Python 3.12.11, three traced 16-query runs measured:

| Path | Peak traced allocation (bytes) | Elapsed seconds |
| --- | --- | --- |
| Retain every receipt | 9,855,302; 10,098,570; 10,052,831 | 4.167; 4.179; 4.210 |
| Checkpoint in batches of four | 2,473,307; 2,469,329; 2,424,652 | 5.052; 5.129; 5.067 |
| Replay saved batches | 3,116,576; 3,082,331; 3,113,750 | 3.925; 3.971; 3.978 |

These instrumented measurements establish bounded collection-retention behavior,
not a speedup or a large-search scaling claim. Profiling still identifies family
replay and Pydantic reconstruction as major costs. A 64-KiB source read under a
64-MiB safety ceiling initially allocated 67,115,430; 67,115,358; 67,115,358 bytes.
Sizing that read from the descriptor-captured file length reduced allocation to
72,102; 72,030; 72,030 bytes while preserving file identity, size, mutation, and
maximum-byte checks. The allocation regression and source-loader negative tests
cover that change. No cache or replay bypass is involved.

## Connected, separate, and external responsibilities

| Concern | Current state | Refactor treatment |
|---|---|---|
| Source ssDNA and source-duplex materialization | Present and connected in complete construction | Verify through selected authorities |
| Local foldback realization | Present and retained-overhead ordered | Preserve witness or exhaustive scope in public results |
| Local basal realization | Present and retained-overhead ordered, with primitive pairing and future-release obligations | Keep local feasibility distinct from adapter completion and global route validity |
| Source partition | Full-span exact authority and optional composition input | Keep it a sibling authority and bind its selected certificate into route inspection |
| Complete route chronology | Connected from source preparation through the requested endpoint | Preserve exact authority joins and endpoint accounting |
| Historical linear-source records | Study-owned regression inputs | Never accepted as runtime defaults or compatibility schemas |
| Exact material specifications | Present in HOP route dependencies | Keep source, primers, adapters, chemistry, and bindings product-owned |
| Physical material instances and observations | Outside HOP | Remain caller-owned |
| Manuscript claims and panel composition | Outside HOP | Remain caller-owned |

## Finite-domain requirement

Retained overhead bounds endpoint sequence positions but does not independently bound
transient source context. Each normalized plan must therefore close payload membership,
enzyme/action records, geometry allocations, material extents, adapter/primer obligations,
and any completion choices before execution identity is computed.
