# Released-foldback geometry and route composition

## Discover geometry before sequence

`search_released_foldback_geometries(catalog=..., request=..., limits=...)`
tries permitted combinations of nick boundaries, caller nicking agents, release
agents and release orientations under the supplied bounds. The request
distinguishes downstream recognition-site placement from complete two-strand separation.

Each feasibility row records oriented footprints, strand-specific nick and
cuts, active-product span, active-oriented nick boundary, minimum precursor
length, per-base domains, correlated Watson–Crick pair domains, and exact
compatible-sequence cardinality. Empty process or pair intersections are
explicit blockers.

The request fixes paired-tract and turn lengths. The search computes the full
geometry cardinality before enumeration, with independent node and hit bounds.
Select a geometry before searching its sequences; apply vendor and application
preferences separately.

## Materialize one selected geometry

`search_released_foldback_precursors(request, limits=...)` intersects one
selected hit with one complete caller-authored IUPAC precursor template.
Correlated base pairs are chosen together, so the search cannot choose one base
without respecting the allowed partner on the other arm.
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
available upstream cross-product was exhausted. The output is a junction-level
route for subsequent complete construction.

`build_released_foldback_precursor_view(...)` and
`build_hairpin_junction_route_view(route)` from `hop_design.views` recheck their
inputs and project the typed released workflow. They accept no independent
foldback input.
