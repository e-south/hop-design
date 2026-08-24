---
doc_id: hop-adr-0020
title: ADR 0020 - Separate design derivation from method chronology
intent: Make design plans declarative and reserve temporal molecular history for method plans.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-23
doc_type: decision
---

# ADR 0020: Separate design derivation from method chronology

## Context

The design plan previously carried route discriminators and ordered mechanics
steps while a separate method plan owned exact molecular states. Two objects
could therefore appear authoritative for physical chronology.

## Decision

`HopSpec` and `ResolvedHopSpec` use v2 schemas with a
`design_derivation_ref`. `HopPlan` uses `hop.plan/v3` and contains a strict
`design_derivation` union. These records explain deterministic component
resolution and evaluation; they contain no ordered method chronology. A
resolved derivation may preserve caller-asserted nick or release projections
needed to derive the encoding.

Only a named method plan owns ordered molecular-state history. Design and
method bundles remain siblings joined, when applicable, by exact encoding-digest
equality. `HopBundle` and design provenance advance to v2.

The removed route fields and old schemas have no aliases or readers.

## Consequences

A compiled design can be authoritative without asserting a production method.
Method availability and feasibility remain independent. Consumers must migrate
to the current strict schemas and cannot infer chronology from a design plan.
