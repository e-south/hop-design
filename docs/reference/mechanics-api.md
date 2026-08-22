---
doc_id: hop-mechanics-api
title: Molecular mechanics API
intent: Define the public foldback, basal, release, and processing-catalog seams.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
---

# Molecular mechanics API

HOP separates physical derivation from caller policy and application identity.
The package accepts explicit events and versioned references; it does not ship
private enzymes, target catalogs, application thresholds, or workspaces.

## Foldback junction

`evaluate_foldback(FoldbackEvaluationRequest)` derives the designed sequence,
canonical junction, source and effective turns, pair observations, mismatch positions,
terminal paired run, longest uninterrupted paired run, and added nucleotide
count. The retained tract must begin at the nick boundary. Explicit evaluation
accepts a cap-only junction when both the retained tract and foldback arm have
length zero; the nonempty turn is preserved and no pair observations are
invented.

`search_foldback_arms(FoldbackSearchRequest, limits=FoldbackSearchLimits)` uses
exact-first deterministic enumeration. It returns the candidate-space size,
nodes examined, hits, and a truthful `complete`, `infeasible`, or `truncated`
status. `max_search_nodes` and `max_hits` are both required.
Search requires a nonempty retained tract because a zero-pair junction has no
foldback-arm design space.

Foldback diagnostics are stable codes `HOP-FOLD-001` through `HOP-FOLD-007`
covering nick/tract geometry, mismatch policy, protected-region mismatches,
run-length bounds, added nucleotides, and turn length.

## Basal junction

`evaluate_basal_pairing(BasalPairingRequest, constraints=...)` first classifies
four physical pairs in S3/S2/S1/S0 order as `watson_crick`, `gt_wobble`, or
`hard_mismatch`. Compact M/W/X strings exist only as interoperability fields.
Whether G:T is treated as wobble is explicit.

The caller-supplied `BasalConstraintProfile` then produces `active`, `reserve`,
or `reject`. A reserve result emits `HOP-BASAL-002`; a resolved compilation
requires `acceptance="allow_reserve"` or adds `HOP-BASAL-003`. Rejected profiles
emit `HOP-BASAL-001` and cannot enter a plan.

## Optional paired stem extension

`evaluate_paired_stem_extension(PairedStemExtensionRequest)` classifies one
pair for every position in two equal-length literal arms. This component sits
between the basal junction and payload stem. It is variable in length and can
preserve intentional mismatches without making the paired payload independently
authored.

The current S3/S2/S1/S0 basal profile remains four positions because it
describes the terminal processing junction, not the entire stem.

## Nick, release, and strand state

`project_released_strand_state(ReleaseProjectionRequest)` accepts an exact
precursor, origin, literal strand-specific nick, duplex cut, optional release
site span, route, and explicit projection constraints. A successful result
includes active and retained strands, sequences, precursor span, active-product
nick boundary, and one lineage record per active-product base.

Every returned molecular sequence is stored 5′→3′. Bottom-active products use
reverse complement and list precursor indexes from high to low. The scanner
omits any motif hit whose resolved top or bottom cut falls outside the supplied
sequence.

Route and nick strand are design-by-contract: bottom-active requires a top
nick; top-active requires a bottom nick. Invalid object geometry raises at
construction. Expected cut and release infeasibility uses `HOP-PROC-001`
through `HOP-PROC-004`.

## Caller-supplied processing catalogs

`ProcessingCatalog` uses schema `hop.processing-catalog/v1` and requires unique
agent IDs across nicking and release entries. Concrete site scanners resolve
forward and reverse geometry only for exact DNA. Symbolic DNA uses
`classify_motif_presence`, which reports `guaranteed`, `possible`, or `absent`
without inventing a concrete event.

## Processing-agent geometry discovery

`search_nicking_placements(catalog=..., target=..., limits=...)` searches one
strand-compatible orientation per nicking agent. `NickingPlacementTarget`
declares a nick boundary and strand, a paired-tract base-pair count, and the
number of turn nucleotides available to preserve a recognition site.

Each feasibility row records target-relative site coordinates and stable
blockers. `HOP-DISC-001` means the site would start before precursor origin;
`HOP-DISC-002` means the site would extend beyond the paired tract and available
turn. A feasible hit records exact or nearest placement, the literal nick,
boundary displacement, and minimum precursor and turn lengths.

Both `max_search_nodes` and `max_hits` are required. Node truncation and result
truncation are reported independently in `truncated_by`; neither is silent.
Hits use a neutral physical order: exact before nearest, then displacement,
required precursor length, required turn length, and agent identity. Catalog
provenance, commercial preference, and application eligibility remain caller
policy. This operation does not enumerate sequence or compile a route.

`search_foldback_precursors(request, limits=...)` is the separate concrete
sequence operation for one selected placement. The caller supplies an IUPAC
template for the required precursor and for any remaining turn extension.
HOP intersects the selected recognition motif with those domains, calculates
the exact candidate-space size before enumeration, derives the returning arm
by reverse complement, and reports the intended and additional nick sites.

`HOP-CAND-001` reports that the caller's template cannot contain the selected
motif. `HOP-CAND-002` reports candidates rejected by the caller's explicit
additional-nick constraint. Both `max_search_nodes` and `max_hits` are hard
budgets with independent truncation evidence. Candidate order uses extra-site
counts, added-sequence GC fraction and homopolymer run, exact sequence, and
content identity. It does not use vendor, catalog-tier, or application rank.

`search_basal_candidates(request, limits=...)` enumerates exact four-position
arm pairs inside two caller-authored IUPAC domains. The request records the G:T
wobble interpretation, the complete `BasalConstraintProfile`, and whether
reserve candidates are selectable. Every returned candidate contains the exact
pairing, complete basal evaluation, full content identity, and one-based
canonical rank. Excluded reserve and reject candidates are counted by their
stable policy reason. Candidate order is compact S3/S2/S1/S0 profile, left arm,
right arm, and content identity; profile buckets, control similarity, mismatch
tier preference, and enzyme/vendor eligibility are not HOP rank inputs.

`search_basal_processing_geometries(catalog=..., request=..., limits=...)`
answers the separate processability question. The request selects one release
agent and orientation, the terminal-nicked strand, a four-base retained-scar
IUPAC template, and an explicit post-nick IUPAC template. Release geometry is
normalized to signed coordinate zero at the top cut, so recognition and
nicking footprints may extend upstream without being forced into a concrete
sequence span.

Each examined nicking agent receives a complete feasibility row. HOP
intersects release, nicking, retained-scar, and post-nick domains; reports the
exact compatible scar cardinality; and returns stable blockers for process
footprint conflicts, empty scar positions, post-nick conflict, incomplete
post-nick coverage, or domain narrowing. `post_nick_domain_mode="compatible"`
allows an agent to narrow the caller domain to a nonempty intersection;
`"preserve"` rejects any narrowing. This explicit choice replaces hidden
assumptions that bases after the terminal nick must be fully degenerate.

Node and hit bounds are independent and never silent. Compatible geometries
use agent identity and signed physical placement order. The result does not
classify basal pairs, select a route, or apply vendor and application policy.

`search_basal_processing_routes(basal_candidates=...,
processing_geometries=..., limits=...)` composes the two typed result sets.
For each examined pair, HOP treats the basal left arm as the retained scar,
checks it against all four geometry domains, and rejects a scar that contains
the selected release motif in either orientation. Compatible routes derive the
terminal nick and surviving strand from the processing geometry and receive a
content identity over both upstream candidates and the normalized release.

The operation evaluates the canonical returned-candidate cross-product. It
reports upstream basal and processing-geometry truncation separately from its
own node and hit bounds; `available_pair_count` therefore describes only that
returned cross-product. Route order follows the upstream physical ranks and
content identity. The operation neither chooses a preferred agent nor proves
continuity with a released foldback state.

`search_released_foldback_geometries(catalog=..., request=..., limits=...)`
evaluates the joint released-foldback geometry before any concrete sequence is
chosen. The request declares the target nick boundary, paired-tract and turn
lengths, exposed-strand route, allowed boundary displacement, and whether the
release recognition site must stay downstream of the nick. A separate
`require_complete_downstream_separation` field requires the partner-strand cut
to clear the active foldback product; recognition-site position alone does not
establish complete separation.

The candidate space is the exact-first nonnegative boundary window crossed with
every caller nicking agent, release agent, and release orientation. Each row
records both oriented recognition footprints, literal nick and duplex cuts,
the active-product span and active-oriented nick boundary, minimum precursor
length, per-base domains, correlated Watson-Crick pair domains, and exact
compatible-sequence cardinality. Empty process or foldback-pair intersections
are explicit blockers.

The search calculates the full candidate-space cardinality arithmetically and
does not consume nodes beyond `max_search_nodes`. `max_hits` independently
bounds compatible results. Content identity and order use only physical inputs:
exact before near, then displacement, boundary, agent identities, and release
orientation. Sequence allocation, warning policy, vendor state, and application
rank remain outside the result.

`search_released_foldback_precursors(request, limits=...)` materializes exact
sequences for one selected `ReleasedFoldbackGeometryHit`. The request's
`precursor_template` must cover the complete required precursor and is the only
sequence domain the caller authorizes. HOP intersects it with every resolved
base domain and every correlated Watson-Crick pair domain before enumeration.

Each pair domain is one independent axis, so its contribution to cardinality
is the number of allowed pairs rather than the product of its two coordinate
domains. Other coordinates remain independent. A zero intersection returns
`infeasible` with `caller_domain_conflict`. `max_search_nodes` and `max_hits`
are independent hard bounds. Candidates contain the exact precursor, its
digest, selected geometry identity, content identity, and canonical physical
rank. The operation does not project a released strand, compose a basal route,
or choose a preferred agent.

## Compiler integration

`ResolvedHopSpec` uses schema `hop.resolved-design/v1` and carries explicit
foldback and basal requests plus an optional terminal nick and release.
`check` aggregates their independent diagnostics. `compile` refuses any error
and emits expected intermediates and typed views into the ordinary verified
bundle.

Without a terminal nick, compilation produces `component_assembly`. It
evaluates the supplied junctions and composes the hairpin encoding without claiming
that HOP generated the components or that a processing route exists. With a
terminal nick, compilation produces `resolved_events`: foldback and basal
pairing remain independent branches, the terminal-nick transition transforms
the basal junction, and insert assembly consumes that state with the foldback
junction and authored payload.

For component assembly, the foldback request's `nick_boundary` is a topology
coordinate marking the retained-tract start. It does not create a `NickEvent`
or assert an experimental nick.

If release is present, a terminal nick is required and its active product must
equal the foldback precursor.
`check` reports `HOP-ROUTE-001` rather than joining unrelated states. The plan
source records the release precursor, or the foldback precursor when release is
absent.

Both paths check internal consistency, not component lineage,
processing-agent eligibility, or experimental performance. Those claims stay
with the caller.
