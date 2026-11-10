# ADR 0016: Discover released-foldback geometry before sequence allocation

## Context

A released foldback depends jointly on a nicking agent, a release agent, the
release-site orientation, the nick boundary, the exposed strand, and the
foldback length. Their recognition motifs and the antiparallel paired tract
constrain the same precursor sequence. Evaluating those constraints one agent
at a time cannot establish that the combined geometry is realizable.

The predecessor search also chose one concrete sequence and mixed physical
compatibility with catalog tiers, warnings, vendor status, and application
ranking. Reproducing that aggregate would hide the distinction between a
possible molecular geometry and a caller's preferred design.

## Decision

HOP provides `search_released_foldback_geometries` as a bounded physical search.
The caller supplies a `ProcessingCatalog`, target nick boundary, paired-tract
length, turn length, exposure route, allowed boundary displacement, whether the
release site must remain downstream of the nick, and whether both strand cuts
must clear the active foldback product.

The search evaluates the complete product of:

- nonnegative nick boundaries in exact-first displacement order;
- caller-supplied nicking agents;
- caller-supplied release agents; and
- forward and reverse release-site orientations.

Each feasibility row records both recognition-site placements, strand-specific
cuts, the released-product extent, the active-strand nick boundary, the minimum
precursor length, every resolved per-base domain, every correlated
Watson-Crick pairing domain, and exact sequence-space cardinality. A compatible
row receives content identity and a neutral rank. HOP does not allocate or
select a concrete sequence in this operation.

`candidate_space_size` is calculated from the independent axes before search.
Only `max_search_nodes` nodes are consumed. `max_hits` independently bounds the
returned compatible rows. Either bound produces explicit `truncated` status.
The result embeds the caller catalog and replays every examined row during
validation.

## Consequences

Cross-agent compatibility now has one public, serializable result. Exact and
near-boundary results can be compared without importing application preferences
or predecessor workspace files.

The result defines a released-foldback sequence domain. The separate
precursor search materializes exact sequences inside caller-authored domains,
and `search_hairpin_junction_routes` projects that exact state before checking
strand continuity with a basal route. Agent selection, complete production-method
resolution, and destination checks remain separate operations.
