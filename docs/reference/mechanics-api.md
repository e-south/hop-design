---
doc_id: hop-mechanics-api
title: Molecular mechanics API
intent: Define the public foldback, basal, release, and processing-catalog seams.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: reference
---

# Molecular mechanics API

HOP separates physical derivation from caller policy and application identity.
The package accepts explicit events and versioned references; it does not ship
private enzymes, target catalogs, application thresholds, or workspaces.
Component evaluators and release projection use the package-root design
facade. Bounded searches use `hop_design.discovery`; workflow projections use
`hop_design.views`.

## On this page

- [Foldback junction](#foldback-junction)
- [Basal junction](#basal-junction)
- [Optional paired stem extension](#optional-paired-stem-extension)
- [Nick, release, and strand state](#nick-release-and-strand-state)
- [Caller-supplied processing catalogs](#caller-supplied-processing-catalogs)
- [Processing-agent geometry discovery](#processing-agent-geometry-discovery)
- [Compiler integration](#compiler-integration)

## Foldback junction

`evaluate_foldback(FoldbackEvaluationRequest)` derives the designed sequence,
canonical junction, source and effective turns, physical pair observations,
non-Watson-Crick positions, terminal and longest uninterrupted Watson-Crick
runs, and added nucleotide count. The retained-tract start is declared once by
`retained_tract_span`; generic foldback evaluation makes no nick claim. Explicit evaluation
accepts a cap-only junction when both the retained tract and foldback arm have
length zero; the nonempty turn is preserved and no pair observations are
invented.

`search_foldback_arms(FoldbackSearchRequest, limits=FoldbackSearchLimits)` uses
exact-first deterministic enumeration. It returns the candidate-space size,
nodes examined, hits, and a truthful `complete`, `infeasible`, or `truncated`
status. `max_search_nodes` and `max_hits` are both required.
Search requires a nonempty retained tract because a zero-pair junction has no
foldback-arm design space.

Foldback diagnostics are stable codes `HOP-FOLD-001` through `HOP-FOLD-006`
covering non-Watson-Crick policy, protected-region pairs, Watson-Crick run bounds,
added nucleotides, and turn length. A G:T pair is
physically classified as `gt_wobble`; these foldback feasibility measurements
still count it as non-Watson-Crick and exclude it from Watson-Crick-only runs.

## Basal junction

`evaluate_basal_pairing(BasalPairingRequest, constraints=...)` first classifies
four physical pairs in S3/S2/S1/S0 order as `watson_crick`, `gt_wobble`, or
`hard_mismatch`. Compact M/W/X strings exist only as interoperability fields.
Literal G:T and T:G pairs are always classified as `gt_wobble`.

The caller-supplied `BasalConstraintProfile` then produces `active`, `reserve`,
or `reject`. A reserve result emits `HOP-BASAL-002`; a resolved compilation
requires `acceptance="allow_reserve"` or adds `HOP-BASAL-003`. Rejected profiles
emit `HOP-BASAL-001` and cannot enter a plan.

`pair_support_index` and `pair_disruption_index` use the declared
`pair-count-weighted@1` dimensionless heuristic. They replay fixed M/W/X
weights; they do not estimate duplex energy, ligation efficiency, enzyme
activity, or experimental success. Thresholds are caller-authored policy.

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

This establishes **sequence-and-cut compatible** geometry: the motif,
orientation, and resolved cut fit the modeled substrate. It does not establish
empirical cleavage efficiency, including activity near a linear end or the
effect of bases outside the recognition site. Those effects vary by enzyme and
reaction context. HOP therefore does not apply one universal minimum-flank
rule. Caller catalogs may record warning codes, but current discovery does not
promote them into feasibility or performance claims. See
[discovery language](../discovery/overview.md).

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

Recognition-motif length is not itself an added-nucleotide measure. Motif
positions can overlap the paired tract or available turn; required precursor
and turn lengths report only the footprint extent that the selected geometry
needs. Degenerate positions are set-valued domains. Neutral effects are domain
narrowing and exact cardinality, not an unqualified synthesis or application
“cost.”

`HOP-CAND-001` reports that the caller's template cannot contain the selected
motif. `HOP-CAND-002` reports candidates rejected by the caller's explicit
additional-nick constraint. Both `max_search_nodes` and `max_hits` are hard
budgets with independent truncation evidence. Candidate order uses literal
precursor sequence, turn extension, and content identity. Extra-site counts,
GC fraction, homopolymer run, vendor status, catalog tier, and application
preference do not determine which candidates survive a hit budget.

`search_basal_candidates(request, limits=...)` enumerates exact four-position
arm pairs inside two caller-authored IUPAC domains. The request records the
complete `BasalConstraintProfile`, including whether observed G:T wobbles may
remain active, and whether
reserve candidates are selectable. Every returned candidate contains the exact
pairing, complete basal evaluation, full content identity, and one-based
contiguous `canonical_ordinal`. Excluded reserve and reject candidates are counted by their
stable policy reason. Candidate order uses literal left arm, right arm, and
content identity. Compact profile, control similarity, mismatch-tier
preference, and enzyme or vendor eligibility do not determine which candidates
survive a hit budget.

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
returned cross-product. Route order follows the upstream canonical ordinals and
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

The paired-tract and turn lengths are inputs to this operation. It does not
search all possible lengths or prove a globally shortest junction. To compare
longer turns or stems, a caller must submit a bounded set of target geometries
and compare their reported physical measurements.

The search calculates the full candidate-space cardinality arithmetically and
does not consume nodes beyond `max_search_nodes`. `max_hits` independently
bounds compatible results. Content identity and order use only physical inputs:
exact before near, then displacement, boundary, agent identities, and release
orientation. Sequence allocation, warning policy, vendor state, and application
preference remain outside the result.

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
digest, selected geometry identity, content identity, and `canonical_ordinal`.
The operation does not project a released strand, compose a basal route,
or choose a preferred agent.

`search_hairpin_junction_routes(released_precursors=..., basal_routes=...,
limits=...)` consumes those two exact upstream result sets without
re-enumerating either search. For each examined pair, HOP projects the selected
precursor through its recorded nick and release cuts and compares the released
active strand with the basal route's surviving strand. A mismatch is reported
as `continuous_strand_mismatch`; a match receives a content-addressed route
with the exact released state.

Release agents at the two ends are not required to match. Their identities and
orientations remain independent physical facts, and HOP applies no enzyme or
application preference. Upstream precursor and basal-route truncation remain
separate from local node and hit truncation. A complete search result means the
available upstream cross-product was exhausted, not that a production method
or destination assembly is complete.

`build_released_foldback_precursor_view(geometry=..., precursor=..., state=...)`
and `build_hairpin_junction_route_view(route)` are available from
`hop_design.views`. They recheck the exact precursor against the
embedded geometry, derive the foldback panel from the selected released state,
and return the typed `released_workflow` view. Neither accepts an independent
foldback input, and neither is part of the root facade.

## Compiler integration

`ResolvedHopSpec` uses schema `hop.resolved-design/v2` and carries explicit
foldback and basal requests plus an optional terminal nick and release.
`check` aggregates their independent diagnostics. `compile` refuses any error
and emits expected intermediates and typed views into the ordinary verified
bundle.

Compilation evaluates the supplied junctions and composes the hairpin encoding
without claiming that HOP generated the components or that a production method
exists. Its `design_derivation` records deterministic component resolution,
not temporal events. A terminal nick and optional release can contribute
explicit resolved-junction geometry without becoming a method plan.

For component assembly, `retained_tract_span.start` is the sole foldback origin.
Actual nick boundaries occur only in discovery, projection, or named-method
contracts that assert strand-specific processing geometry.

If release is present, a terminal nick is required and its active product must
equal the foldback precursor.
`check` reports `HOP-ROUTE-001` rather than joining unrelated states. The plan
source records the release precursor, or the foldback precursor when release is
absent.

Both forms check design consistency, not process lineage,
processing-agent eligibility, or experimental performance. Those claims stay
with the caller.
