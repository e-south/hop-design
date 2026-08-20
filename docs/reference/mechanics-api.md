---
doc_id: hop-mechanics-api
title: Molecular mechanics API
intent: Define the public foldback, basal, release, and processing-catalog seams.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# Molecular mechanics API

HOP separates physical derivation from caller policy and application identity.
The package accepts explicit events and versioned references; it does not ship
private enzymes, target catalogs, application thresholds, or workspaces.

## Foldback junction

`evaluate_foldback(FoldbackEvaluationRequest)` derives the designed sequence,
canonical junction, source and effective turns, pair observations, mismatch positions,
terminal paired run, longest uninterrupted paired run, and added nucleotide
count. The retained tract must begin at the nick boundary.

`search_foldback_arms(FoldbackSearchRequest, limits=FoldbackSearchLimits)` uses
exact-first deterministic enumeration. It returns the candidate-space size,
nodes examined, hits, and a truthful `complete`, `infeasible`, or `truncated`
status. `max_search_nodes` and `max_hits` are both required.

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

## Compiler integration

`ResolvedHopSpec` uses schema `hop.resolved-design/v1` and carries explicit
foldback, basal, terminal-nick, and optional release requests. `check` aggregates
their independent diagnostics. `compile` refuses any error, records ordered
`resolved_events` state-graph steps, and emits expected intermediates and typed
views into the ordinary verified bundle. Foldback and basal pairing are
independent branches. A terminal-nick transition transforms the basal junction;
insert assembly then consumes that state with the foldback junction and
authored payload.

If release is present, its active product must equal the foldback precursor.
`check` reports `HOP-ROUTE-001` rather than joining unrelated states. The plan
source records the release precursor, or the foldback precursor when release is
absent.

This integration checks internal consistency, not processing-agent eligibility
or experimental performance. Those claims stay with the caller.
