---
doc_id: hop-adr-0014
title: ADR 0014 - Separate basal pairing from processing geometry
intent: Keep four-base pair classification independent from release and terminal-nick feasibility.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
doc_type: decision
---

# ADR 0014: Separate basal pairing from processing geometry

## Context

An exact four-base arm pair can satisfy a `BasalConstraintProfile` without
being producible by a chosen release and terminal-nicking geometry. The
predecessor combined pair classification, enzyme catalog policy, motif overlap,
a hidden fully-degenerate downstream rule, application ranking, and report
selection. Reproducing that aggregate would make a physical HOP result depend
on vendor metadata and one study's desired panel.

Terminal placements also use signed coordinates. A release top cut is origin
zero; its recognition site and the nicking footprint may extend upstream of
that boundary. Ordinary nonnegative sequence spans cannot represent this
design coordinate frame without shifting or discarding relevant geometry.

## Decision

HOP keeps `search_basal_candidates` and
`search_basal_processing_geometries` as separate bounded operations.

The processing-geometry request selects one caller-supplied release agent and
orientation, the terminal-nicked strand, a four-base retained-scar IUPAC
domain, an explicit post-nick IUPAC domain, and whether that post-nick domain
may be narrowed or must be preserved. The release top cut is signed coordinate
zero. HOP evaluates every examined nicking agent at the exact terminal boundary
and returns:

- the normalized release footprint and cuts;
- the oriented nicking footprint and exact nick boundary;
- the resolved base domain at every affected signed coordinate;
- the four retained-scar domains and their exact cardinality;
- the resolved post-nick domains;
- stable geometry blockers; and
- independent node and returned-hit truncation evidence.

Catalog eligibility, warning-code policy, commercial status, candidate profile,
control similarity, and application desirability are not inputs to physical
geometry order. A caller that requires an unchanged degenerate region chooses
`post_nick_domain_mode="preserve"`; HOP does not infer that rule from `N` or
from a particular method.

## Consequences

Pairing and processability can be compared and evolved independently. A study
may intersect the two result sets and apply its own rank without making that
rank part of either HOP kernel. Joint route discovery remains a later bounded
composition of explicit results rather than a monolithic scar-nick compiler.

The signed coordinates are local design coordinates, not general sequence
`Boundary` objects. Concrete compiled molecules continue to use zero-based,
half-open nonnegative spans.
