---
doc_id: hop-released-foldback-routes-reference
title: Released-foldback geometry and route composition
intent: Define bounded release geometry, exact precursor materialization, and cross-junction continuity.
audience:
  - API consumers
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-24
doc_type: reference
---

# Released-foldback geometry and route composition

## Discover geometry before sequence

`search_released_foldback_geometries(catalog=..., request=..., limits=...)`
crosses bounded nick boundaries with caller nicking agents, release agents, and
release orientations. The request distinguishes downstream recognition-site
placement from complete two-strand separation.

Each feasibility row records oriented footprints, strand-specific nick and
cuts, active-product span, active-oriented nick boundary, minimum precursor
length, per-base domains, correlated Watson–Crick pair domains, and exact
compatible-sequence cardinality. Empty process or pair intersections are
explicit blockers.

Paired-tract and turn lengths are request inputs. The search does not vary all
lengths, prove a globally shortest junction, choose a sequence, or apply vendor
and application preferences. It computes the full geometry cardinality before
enumeration. Node and hit bounds remain independent.

## Materialize one selected geometry

`search_released_foldback_precursors(request, limits=...)` intersects one
selected hit with one complete caller-authored IUPAC precursor template.
Correlated base pairs are one choice axis rather than two independent bases.
An empty intersection returns `infeasible` with `caller_domain_conflict`.

Each exact candidate contains its precursor, digest, geometry identity, content
identity, and `canonical_ordinal`. The operation does not project a released
strand, compose a basal route, or choose a preferred agent.

## Join the two junctions

`search_hairpin_junction_routes(released_precursors=..., basal_routes=...,
limits=...)` consumes two exact upstream result sets. For every examined pair,
HOP replays the selected precursor through its recorded nick and cuts, then
requires the released active strand to equal the basal surviving strand.
Failure is `continuous_strand_mismatch`.

The two end-agent identities remain independent. Upstream incompleteness is
reported separately from local node and hit truncation. `complete` means the
available upstream cross-product was exhausted; it does not mean a production
method or destination assembly is complete.

`build_released_foldback_precursor_view(...)` and
`build_hairpin_junction_route_view(route)` from `hop_design.views` recheck their
inputs and project the typed released workflow. They accept no independent
foldback input and make no new method claim.
