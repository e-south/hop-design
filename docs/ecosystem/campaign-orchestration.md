---
doc_id: hop-campaign-orchestration
title: HOP in a campaign orchestration stack
intent: Position HOP as a hairpin-specific semantic backend for broader biological design systems.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: explanation
journey:
  - integrate
---

# HOP in a campaign orchestration stack

A campaign system can generate sequences, combine objectives, and select which
candidates to test. HOP defines what a hairpin candidate means and whether a
named method deterministically realizes it.

```text
campaign orchestrator
    -> proposes payloads, domains, or candidate designs
HOP design and discovery
    -> returns deterministic encodings, structured diagnostics, and neutral ordinals
caller selection
    -> records the objective and chosen candidate identity
HOP named-method realization
    -> returns an exact destination-neutral product and lineage
downstream systems
    -> place, assess, execute, and observe
```

## Adapter roles

| Campaign-facing role | HOP behavior |
| --- | --- |
| Deterministic compiler | Compile structured anatomy into a normalized, feature-partitioned encoding. |
| Candidate generator | Enumerate compatible geometries under explicit bounds. |
| Hard constraint | Reject invalid anatomy or incompatible relationships. |
| Measurement provider | Expose structured measurements that a caller may project into a named objective. |
| Post-selection compiler | Resolve one selected exact design through a named method. |
| Metadata source | Attach feature partitions, digests, diagnostics, and lineage. |

The adapter must preserve HOP's structured result. It must not collapse
`complete`, `infeasible`, and `truncated` into a generic no-hit value; present
`canonical_ordinal` as a score; or discard bundle and projection digests.

HOP does not depend on a campaign framework, and generic campaign primitives do
not replace HOP's domain types.
