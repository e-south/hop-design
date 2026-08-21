---
doc_id: hop-mechanics-api
title: Molecular mechanics API
intent: Define the public foldback, basal, release, and processing-catalog seams.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-21
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
policy. This operation does not enumerate filler bases or compile a route.

## Compiler integration

`ResolvedHopSpec` uses schema `hop.resolved-design/v1` and carries explicit
foldback and basal requests plus an optional terminal nick and release.
`check` aggregates their independent diagnostics. `compile` refuses any error
and emits expected intermediates and typed views into the ordinary verified
bundle.

Without a terminal nick, compilation produces `component_assembly`. It
evaluates the supplied junctions and composes the final insert without claiming
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
