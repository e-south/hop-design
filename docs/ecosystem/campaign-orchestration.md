# HOP in a campaign orchestration stack

A campaign system can generate sequences, combine objectives, and select which
candidates to test. HOP derives hairpin sequence anatomy and checks how exact
input materials pass through named methods.

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
| Deterministic compiler | Derive a normalized sequence and its named regions from structured anatomy. |
| Candidate generator | Enumerate compatible geometries under explicit bounds. |
| Hard constraint | Reject invalid anatomy or incompatible relationships. |
| Measurement provider | Return measurements that a caller may use in a declared objective. |
| Post-selection compiler | Resolve one selected exact design through a named method. |
| Metadata source | Attach feature partitions, digests, diagnostics, and lineage. |

The integration code must preserve HOP's structured result. It must not collapse
`complete`, `infeasible`, and `truncated` into a generic no-hit value; present
`canonical_ordinal` as a score; or discard bundle and projection digests.

HOP does not depend on a campaign framework, and generic campaign primitives do
not replace HOP's domain types.
