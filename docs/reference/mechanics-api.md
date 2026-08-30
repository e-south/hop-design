---
doc_id: hop-mechanics-api
title: Molecular mechanics reference map
intent: Route each physical competency question to one authoritative reference.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: index
journey:
  - compile
  - discover
---

# Molecular mechanics reference map

HOP separates component evaluation, processing geometry, route composition,
and caller policy. Choose the narrowest question; no single operation is a
global hairpin optimizer or a complete laboratory method.

| Question | Public operation | Detailed reference |
| --- | --- | --- |
| What physical pairs and spans define this foldback, basal junction, or stem extension? | root evaluators | [Component evaluation](component-evaluation.md) |
| What released strand follows from these literal cuts? | `project_released_strand_state` | [Component evaluation](component-evaluation.md#released-strand-projection) |
| Which nicking placement or exact precursor satisfies this selected geometry? | discovery placement and precursor searches | [Processing discovery](processing-discovery.md) |
| Which basal arm pairs, processing geometries, and terminal routes compose? | bounded basal searches | [Processing discovery](processing-discovery.md#basal-searches) |
| Which nick/release geometry can produce a released foldback, and can it join a basal route? | released-foldback searches | [Released-foldback routes](released-foldback-routes.md) |
| Which exact complete routes follow from strict local requests and a verified design? | `compile_construction` and construction projections | [Python API](python-api.md#payload-centered-construction) |
| How does a selected set of components become a verified encoding? | `check` and `compile` | [Compiler integration](component-evaluation.md#compiler-integration) |

## Public seams

- Common component evaluation and released-state projection use `hop_design`.
- File-oriented complete construction and neutral scientific projections use
  `hop_design.construction`.
- Bounded searches, scanners, strict requests, limits, results, and candidates
  use `hop_design.discovery`.
- Renderer-independent projections use `hop_design.views`.
- File-oriented complete-route chronology belongs to
  `hop_design.construction`; independently named production-method chronology
  belongs to `hop_design.methods`.

Every bounded search reports `complete`, `infeasible`, or `truncated`, with
node and hit bounds kept independent. `canonical_ordinal` is presentation
order, never an optimization score. Sequence-and-cut compatibility does not
establish empirical cleavage efficiency or destination fitness.

For facade signatures, see the [Python API](python-api.md). For the language
relationships that these operations enforce, see
[relationships and invariants](../language/relationships-and-invariants.md).
