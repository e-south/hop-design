---
doc_id: hop-ontology
title: HOP Design ontology
intent: Define the canonical public molecular and compiler vocabulary.
audience:
  - users
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# HOP Design ontology

`Payload` is the input sequence to be paired. `ExactPayload` uses only
`A/C/G/T`; `DegeneratePayload` retains DNA IUPAC symbols. Its paired payload arm
is always derived by reverse complement.

`FoldbackJunction` is the contiguous physical junction between the authored
payload arm and its returning paired arm. It contains a retained stem-forming
tract, the short unpaired `turn`, a `foldback_arm`, and one ordered physical
pair observation for every aligned position.

`BasalJunction` is the paired junction at the open end of the payload duplex.
It has declared left and right arms, a base-pair count, and ordered physical
pair observations. Nicked and surviving strand roles belong to processing
events and views, not to the junction itself.

`JunctionPairObservation` records literal left/right bases, antiparallel
indexes, and a `watson_crick`, `gt_wobble`, or `hard_mismatch` call. Exact
defaults and evaluated noncanonical junctions use this same representation.

`ProcessingRoute` is a reusable physical implementation that produces a
resolved foldback and basal junction. `resolved_events` records explicit
caller-supplied release nick, optional release, foldback, basal-pairing,
terminal-nick, and insert-assembly transitions. The generic direct-synthesis
route is a synthetic software demonstration, not a lab protocol.

`BasalConstraintProfile` is explicit caller policy applied after physical pair
classification. Its active, reserve, and reject decisions are not molecular
pair kinds. Application thresholds remain with their owners.

`ProcessingCatalog` is a strict caller-supplied set of nicking and release
agents. HOP can resolve concrete site geometry or classify symbolic motif
presence as `guaranteed`, `possible`, or `absent`; it ships no private or
application-specific processing catalog.

`ReleasedStrandState` records the active product, retained partner, literal
strand roles, cut and nick boundaries, precursor span, and per-base coordinate
lineage after one explicit release event. Molecular sequences are stored 5′→3′;
bottom-strand lineage therefore traverses top-precursor indexes in reverse.

`WorkflowView` is the renderer-independent scientific view contract. It owns
panels, tracks, features, pair calls, and strand direction. SVG is one
deterministic rendering and cannot change the molecular state.

`Diagnostic` is a stable, machine-readable explanation of expected design
infeasibility. Invalid schemas or corrupt software configuration are exceptions,
not diagnostics.
