---
doc_id: hop-adr-0029
title: ADR 0029 - Separate source partition from junction geometry
intent: Keep auxiliary cleanup nicks and size selection out of foldback and basal local targets.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
amends:
  - hop-adr-0026
---

# ADR 0029: Separate source partition from junction geometry

## Context

A linear duplex may require several nicks before denaturation and length
selection. Some nicks define the retained foldback or basal-bearing fragments;
others subdivide discarded material so a physical size-selection step can
exclude it. Those auxiliary cuts affect the whole source partition but do not
change the biological payload or the geometry of either local junction.

Treating every nick near one end as basal geometry would make a local target
own a route-wide cleanup strategy. It would also couple the ontology to one
historical precursor layout.

## Decision

Source partitioning is a sibling bounded discovery authority. Its input is:

- an exact duplex source and payload mapping;
- a caller-owned characterized-enzyme snapshot;
- enzymes provisioned for strand exposure;
- one exact fragment-length rule;
- required survivor strand spans; and
- finite enzyme-subset search bounds.

The candidate domain is every nonempty provisioned nickase subset up to the
declared width. Applying an enzyme means applying all actionable sites in the
exact source state. Replay derives nicked duplex, denatured fragments, selected
fragments, and the function of each nick. A candidate is accepted only when
the selected fragment relation equals the required survivors.

Foldback and basal targets retain only local sequence and reaction geometry.
PCR handles, primer binding, and Type IIS release remain endpoint-
materialization questions. Complete route composition may claim only the
authorities explicitly included and globally reassessed on exact molecular
states.

## Consequences

A known precursor can serve as a regression oracle without becoming the source
schema. A study can vary enzyme catalogs, length rules, and required survivor
spans while preserving the same payload and local-junction questions.

Search status remains `complete`, `infeasible`, or `truncated`. Enzyme-subset
order is deterministic replay metadata, never a score. Catalog provenance,
empirical performance, column recovery, PCR thermodynamics, and experimental
selection remain caller-owned evidence or policy.
