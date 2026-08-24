---
doc_id: hop-processing-discovery-reference
title: Processing and basal discovery
intent: Define bounded nicking, precursor, basal, and terminal-route searches.
audience:
  - API consumers
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-24
doc_type: reference
---

# Processing and basal discovery

All contracts and operations on this page come from `hop_design.discovery`.
`ProcessingCatalog` requires unique IDs across caller-supplied nicking and
release agents. Exact scanners resolve oriented events; symbolic motif
classification reports `guaranteed`, `possible`, or `absent` without inventing
a concrete cut.

## Nick placement and precursor sequence

`search_nicking_placements(catalog=..., target=..., limits=...)` tests bounded
agent orientations against one requested boundary, strand, paired-tract length,
and available turn. It establishes **sequence-and-cut compatible** geometry,
not empirical cleavage efficiency near an end or under a reaction condition.
HOP therefore applies no universal minimum-flank rule.

`HOP-DISC-001` means a site starts before precursor origin; `HOP-DISC-002`
means it extends beyond available paired tract and turn. Hits use neutral
physical order. Catalog provenance and application preference remain caller
policy.

`search_foldback_precursors(request, limits=...)` consumes one selected
placement and caller-authored IUPAC domains. It intersects motif and sequence
domains, calculates exact cardinality, derives the returning arm, and reports
additional nick sites. `HOP-CAND-001` identifies an empty motif intersection;
`HOP-CAND-002` identifies rejection by an explicit additional-nick constraint.
Candidate order is literal precursor sequence, turn extension, and content
identity—not GC, homopolymers, vendor state, or application preference.

## Basal searches

`search_basal_candidates(request, limits=...)` enumerates exact four-base arm
pairs from two IUPAC domains and applies the complete caller policy. Each hit
contains its literal pairing, evaluation, content ID, and contiguous ordinal.
Excluded reserve and reject rows are counted by stable reason. Order uses left
arm, right arm, and content identity; M/W/X profile is an annotation, not a
hit-budget preference.

`search_basal_processing_geometries(catalog=..., request=..., limits=...)`
separately asks which terminal nick and release geometry can process a declared
scar and post-nick domain. Geometry is normalized to signed coordinate zero at
the top cut. `post_nick_domain_mode="compatible"` permits explicit nonempty
narrowing; `"preserve"` rejects any narrowing. Every examined agent receives a
feasibility row.

`search_basal_processing_routes(...)` joins the two returned result sets. It
treats the basal left arm as retained scar, rejects domain conflicts and a
retained release motif, and derives the terminal nick and surviving strand.
The result reports upstream and local truncation separately. Route order uses
the two upstream ordinals and content identity. It does not choose an agent or
prove continuity with a released foldback.

Every search requires `max_search_nodes` and `max_hits`. The two limits fire
independently and are never replaced by silent truncation.
