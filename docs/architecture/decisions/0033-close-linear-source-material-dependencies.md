---
doc_id: hop-adr-0033
title: ADR 0033 - Close linear-source material dependencies
intent: Make source preparation, partitioning, auxiliary materials, and endpoint navigation one portable HOP result.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-31
doc_type: decision
amends:
  - hop-adr-0010
  - hop-adr-0026
  - hop-adr-0029
---

# ADR 0033: Close linear-source material dependencies

## Context

Complete construction currently begins at an exact duplex. The named method can
derive an expected source-PCR duplex from a source oligo and primers, and source
partitioning can independently resolve cleanup nicks and selected fragments.
Neither authority is connected to the complete construction result. A caller
can therefore receive a valid downstream route without one portable account of
the source ssDNA, source primers, source preparation, or selected partition.

## Decision

### Product and evidence boundary

HOP owns every exact molecular specification and deterministic transformation
required to inspect or execute a digital route. A caller owns procurement,
physical instances, protocols, observations, quality control, and biological
interpretation. A material specification is not evidence that a physical
material exists.

### Payload and route roots

The design input remains the final duplex payload. The first external material
in the linear-source route is one ssDNA source specification. The route family
maps final-payload coordinates into source coordinates and derives every paired
sequence. The shared payload contract does not require one contiguous source
interval; the current linear-source family does.

### Design and replay modes

Design mode derives source and auxiliary sequences under explicit policies.
Replay mode fixes exact historical materials and verifies them. Fixed materials
are ordinary constraints and receive no privileged identifiers or defaults.

### Source preparation

A content-addressed source-preparation authority records:

- one exact source ssDNA material;
- two exact source-materialization primers;
- terminal primer bindings outside the payload;
- exact copied duplex products and complete antiparallel pairings; and
- output chemistry and per-base sequence lineage.

Its output must equal the exact duplex that seeds the existing downstream
`ConstructionProgram`. The source-preparation authority precedes that program
inside the complete realization. It does not model PCR conditions, cycles,
yield, or success.

### Materials and contextual use

The foundational material is generic exact DNA with topology, terminal
chemistry, explicit region annotations, and content identity. Source, primer,
adapter, and destination terms describe contextual use in a route. Production
lineage is expressed by transformation edges rather than an overloaded
`synthesized`, `pcr_derived`, or `purified` adjective.

Material resolution has three explicit modes:

- `derive`: HOP derives one exact material under a complete deterministic rule;
- `constrain`: HOP derives one exact material within caller-supplied bounds; and
- `fixed`: the caller supplies an exact material that HOP validates.

No hidden thermodynamic or empirical ranking is introduced. Source primers bind
only invariant construction sequence and may not overlap the payload. Handle
selection begins from fixed or caller-supplied reusable candidates; arbitrary
handle generation remains unsupported until its sequence-quality rules exist.

### Source partition

Source partition remains a sibling local authority. A complete route may bind
one explicit replay-verified source-partition realization. Composition verifies
that its source duplex, molecular enzyme definitions, concurrent nick program,
fragment rule, and required survivors equal the route states. Rejected routes
retain sealed pre-partition candidates so the exact rejection class replays at
the model boundary. Cleanup nicks do not become basal geometry.

### Operations and stages

The operation vocabulary remains a versioned closed union. Source preparation
uses exact template copying; downstream construction retains assessed enzyme
phases, separation, partition, association, joins, endpoint copying, and
optional end generation. Multiple joins in one laboratory stage remain
separate bonds. Stage identity and molecular consequences, not procedure names,
are authoritative.

### Identity, grouping, and selection

Exact local realizations, complete routes, materials, transformations, and
endpoint products retain separate content identities. Geometry and endpoint
groups are reversible projections. Selection stores stable references and
never removes alternatives, reruns search, or becomes a hidden recommendation.

### Endpoint and payload-space semantics

The current endpoints remain `ssdna_hairpin`, `hairpin_pcr_duplex`, and
`clone_ready_duplex`; the last is destination-neutral and establishes only
exact cohesive ends. Exact payload replay and bounded-pattern compatibility are
distinct. One exact representative can never establish pool-wide compatibility.

### Sequence annotations

Molecular sequences normalize to uppercase. Payload, construction flank,
recognition site, primer-binding region, adapter pairing region, handle, paired
arm, and destination interface are explicit typed spans. Letter case carries no
scientific meaning.

## Consequences

An external user can inspect every molecular dependency without a Research
Studies checkout. Research Studies becomes a caller that freezes HOP requests
and results, selects routes, records physical parts and observations, and builds
study-specific plots.

This is one intentional pre-1.0 schema change. It adds no compatibility aliases,
fallback readers, study imports, inventory manager, dashboard, thermodynamic
model, or physical-success claim. Existing released bundle bytes remain the
historical authorities they already are and are not reinterpreted as closed
source-ssDNA routes.
