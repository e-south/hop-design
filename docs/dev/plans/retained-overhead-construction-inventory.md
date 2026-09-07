---
doc_id: retained-overhead-construction-inventory
title: Retained-overhead construction implementation inventory
intent: Record the reusable boundaries, completed semantic cutover, and downstream work.
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

This is an implementation inventory for the breaking construction refactor. It is not a scientific evidence snapshot.

## Reusable implementation

- `models.payload`, construction payload references, and source maps already preserve exact and patterned payload identity without permitting route code to edit the payload.
- Characterized enzyme records already carry strict recognition, strand, cleavage, substrate-state, terminal-state, and provenance facts.
- Foldback and basal kernels already enumerate exact sequence placements and return explicit molecular failures.
- Foldback and basal realization records already preserve enzyme bindings, literal pairing, retained and released sequence, bonds, material roles, and deterministic identities.
- Complete construction already composes selected verified local authorities, derives source and auxiliary materials, replays endpoint-specific molecular transitions, binds optional source-partition evidence, and verifies endpoint encodings.
- File-oriented public receipts, canonical JSON, create-only publication, replay verification, and typed projections provide the correct authority boundary.

## Retired surfaces

- `hop.local-neighborhood-request/v3` made one exact geometry target plus a radius policy the public search domain.
- Radius policy models and traversal made distance from one target the primary local-search ordering.
- The former local result stored feasibility inside its completion enum and reported radius shells rather than absolute retained-overhead levels.
- Local execution identity embedded the radius policy and traversal bounds.
- Local projections and CLI language described that radius-based search model.

The active strict schemas remove these inputs. There is no compatibility reader or
translation layer.

## Implemented boundaries

- Foldback search is ordered by absolute retained non-payload overhead.
- Basal search uses primitive pairing and future-release obligations rather than named
  profiles.
- Source-partition authorities certify both complete source strands across the inclusive
  maximum-fragment ladder 11--15.
- Selected complete routes bind exact source preparation, source partition, molecular
  chronology, and endpoint evidence.
- Public projections expose local overhead, basal enzyme-action minima, exact source
  partitions, route navigation, and selected route trajectories.

## Remaining product requirements

- Public local discovery still returns an in-memory result. Sequence-domain partitioning
  is available, but durable bounded result streaming and producer-bound resumption are
  not implemented in HOP. Client-side checkpoints do not satisfy this product contract.
- Source-partition discovery evaluates enzyme programs on one supplied exact source
  duplex. Its full-span certificate does not establish bounded scaffold-sequence or
  context-extension solving around local and primer obligations. That completion search
  remains separate implementation work.
- The post-release construction changes require a distinct package version and immutable
  producer cutoff before downstream formal execution. A wheel bearing the published
  version number is insufficient to distinguish these semantics.

## Downstream work

- Research Studies must freeze new finite line inputs and regenerate the affected
  computational authorities, tables, and figures.
- manufold may import only explicitly accepted immutable study assets.
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

## Connected, separate, and external responsibilities

| Concern | Current state | Refactor treatment |
|---|---|---|
| Source ssDNA and source-duplex materialization | Present and connected in complete construction | Reuse and verify through the new selected authorities |
| Local foldback realization | Present and retained-overhead ordered | Reuse and verify in the formal study run |
| Local basal realization | Present and retained-overhead ordered, with primitive pairing and future-release obligations | Keep local feasibility distinct from adapter completion and global route validity |
| Source partition | Full-span exact authority and optional composition input | Keep it a sibling authority and bind its selected certificate into route inspection |
| Complete route chronology | Connected from source preparation through the requested endpoint | Preserve exact authority joins and endpoint accounting |
| Historical linear-source records | Preserved study evidence and regression inputs | Never accepted as runtime defaults or compatibility schemas |
| Exact material specifications | Present in HOP route dependencies | Keep source, primers, adapters, chemistry, and bindings product-owned |
| Physical material instances and observations | Outside HOP | Remain owned by Research Studies |
| Manuscript claims and panel composition | Outside HOP | Remain owned by manufold |

## Finite-domain requirement

Retained overhead bounds endpoint sequence positions but does not independently bound
transient source context. Each normalized plan must therefore close payload membership,
enzyme/action records, geometry allocations, material extents, adapter/primer obligations,
and any completion choices before execution identity is computed.
