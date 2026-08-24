---
doc_id: hop-adr-0015
title: ADR 0015 - Compose basal pairs with terminal processing
intent: Define the bounded physical join without importing caller selection policy.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
doc_type: decision
---

# ADR 0015: Compose basal pairs with terminal processing

## Context

Basal pairing and terminal processing answer different questions. A
`BasalCandidate` proves exact arm pairing under a caller-supplied constraint
profile. A `BasalProcessingGeometryHit` proves that one release footprint and
terminal nicking footprint admit a four-base retained-scar domain. Neither
object alone proves that a particular exact scar works in that geometry.

The predecessor joined these concerns while also applying enzyme preference,
profile buckets, controls, and application rank. Copying that aggregate would
make HOP route identity depend on caller policy. Leaving the join entirely to
callers would duplicate a physical compatibility rule and make cross-consumer
results harder to replay.

## Decision

HOP provides `search_basal_processing_routes` as a bounded composition of two
typed search results.

For every examined Cartesian pair:

- the basal left arm is the retained scar;
- every scar base must satisfy the corresponding processing-geometry domain;
- the retained scar must not contain the selected release motif in either
  orientation;
- the terminal nick is derived from the processing geometry; and
- the surviving strand is the strand opposite the terminal-nicked strand.

Compatible routes receive content identity over the normalized release, exact
basal candidate, and exact processing geometry. Order follows upstream physical
ranks and content identity. HOP returns all compatible routes within the
caller-supplied node and hit budgets. It does not select a preferred nicking
agent or apply application desirability.

The result records four independent incompleteness sources: upstream basal
search, upstream processing-geometry search, route-node budget, and returned-hit
budget. `available_pair_count` is the Cartesian product of the two returned
upstream hit sets. It is not presented as the global route-space cardinality
when either input search is truncated. HOP computes the count arithmetically
and iterates only through the route-node budget; it does not materialize the
unexamined Cartesian product.

## Consequences

The retained-scar join has one public contract and can be replayed after JSON
serialization. Callers can add selection policy after receiving physically
valid routes without changing HOP identity or order.

This object proves only the basal processing join. The later
`search_hairpin_junction_routes` operation projects an exact released-foldback
precursor and requires its active strand to equal this route's surviving
strand. Neither object proves that a complete production method has been
selected.
