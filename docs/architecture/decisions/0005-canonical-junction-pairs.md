---
doc_id: hop-adr-0005
title: ADR 0005 - Canonical junction pair observations
intent: Record one physical junction representation for exact and noncanonical pairs.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-20
doc_type: decision
amended_by: hop-adr-0021
---

# ADR 0005: Canonical junction pair observations

## Context

Catalog junctions previously required perfect complementarity while evaluation
models could report wobble and mismatch states. The same noun therefore had two
incompatible physical meanings.

## Decision

`FoldbackJunction` and `BasalJunction` contain ordered
`JunctionPairObservation` values. Each observation records literal bases,
antiparallel indexes, and one `watson_crick`, `gt_wobble`, or `hard_mismatch`
call. Exact catalog defaults and evaluated near matches instantiate the same
types. Feasibility thresholds remain in evaluation and caller policy.

## Consequences

Pair observations cover every aligned position, including mismatches. A matched
only pair map is not a second authority. Views and serialized intermediates
consume the canonical junction object. This pre-release correction remains in
the `v1` schemas because no public artifact preceded it.
