---
doc_id: hop-adr-0017
title: ADR 0017 - Materialize released-foldback precursors inside caller domains
intent: Define the exact-sequence handoff after geometry discovery without inventing sequence or ranking policy.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
---

# ADR 0017: Materialize released-foldback precursors inside caller domains

## Context

Released-foldback geometry discovery returns per-base domains and correlated
Watson-Crick pair domains. Those domains prove that a process geometry admits
one or more sequences, but they do not authorize HOP to choose arbitrary bases.
A caller may already constrain part or all of the precursor through a payload,
synthesis design, inherited component, or other upstream intent.

Expanding every geometry before applying those constraints wastes work and can
present invented filler as a design decision. Combining sequence allocation
with basal-route composition would also make one operation responsible for two
independent molecular choices.

## Decision

HOP provides `search_released_foldback_precursors` for one selected
`ReleasedFoldbackGeometryHit`. The request includes one complete IUPAC
`precursor_template` whose length equals the geometry's required precursor
extent. HOP intersects that template with every geometry base domain and with
each correlated foldback pair domain before enumeration.

Pair coordinates are enumerated as one correlated axis. Their cardinality is
therefore the number of allowed base pairs, not the product of two independent
base domains. All remaining coordinates are independent axes. Axis and choice
order are deterministic and physical; they do not encode vendor, catalog-tier,
study, or application preference.

The result reports exact intersected cardinality before allocating candidates.
`max_search_nodes` bounds examined exact sequences and `max_hits` independently
bounds returned candidates. A zero intersection is `infeasible` with the
`caller_domain_conflict` blocker. Either budget produces `truncated`; no
partial search is reported as complete. Every candidate has the exact sequence,
sequence digest, selected geometry identity, content identity, and one-based
rank.

Specialized request and result models remain under
`hop_design.models.discovery`. Only the operation is added to the package-root
facade.

## Consequences

The selected geometry now has a bounded, replayable exact-sequence handoff.
HOP never treats the geometry's unconstrained `A/C/G/T` positions as permission
to invent bases outside a caller-authored template.

This operation does not project a released strand, compose a basal route,
choose a preferred process agent, or assert a complete production method.
`search_hairpin_junction_routes` consumes its typed result and the separate
basal-processing result without re-enumerating either input.
