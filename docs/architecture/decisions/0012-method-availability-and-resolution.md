---
doc_id: hop-adr-0012
title: ADR 0012 - Method availability and resolution
intent: Separate sequence identity, method implementation, method feasibility, and destination readiness.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
doc_type: decision
---

# ADR 0012: Method availability and resolution

## Context

A hairpin sequence may be authoritative even when HOP cannot produce it through
a particular method. Treating sequence validity, method support, and physical
feasibility as one status would either reject real records or make a strict
method permissive.

Method names also need to survive roadmap changes. Labels such as “reference,”
“future,” or “alternative” describe project status, not molecular
transformations.

## Decision

HOP identifies method families by their transformation:

- `linear-source-multinick-size-selection-hairpin-pcr@1`;
- `circular-precursor-exonuclease-selection-multidigest-hairpin-pcr@1`.

Availability and resolution are independent fields:

| Facet | Values | Meaning |
| --- | --- | --- |
| `implementation_status` | `available`, `unavailable` | Whether this HOP version implements the named method |
| `resolution_status` | `not_evaluated`, `complete`, `infeasible`, `truncated` | What a bounded method evaluation established for one request |

An unavailable method can only be `not_evaluated`. An infeasible result requires
an error diagnostic. A complete result cannot carry an error diagnostic and
must contain a full method plan.

The linear-source method retains the reverse-complement payload invariant. A
sequence requiring noncomplementary payload partners is not accepted by
loosening that schema; it is evaluated as infeasible for this method. Another
production method requires its own request and state contract.

Destination readiness is separate again. `RestrictionDigestProduct` records a
destination-neutral restriction product and projection. It becomes an
`AssemblyFragment` only after a caller supplies a destination, orientation, and
compatible ends.

## Consequences

Study records can state sequence identity and provenance without implying that
every HOP method can produce them. Workflows fail explicitly for unavailable or
infeasible methods and never substitute another path. New method families may
reuse molecular-state primitives, but HOP does not expose a user-authored
reaction graph or speculative plugin registry.
