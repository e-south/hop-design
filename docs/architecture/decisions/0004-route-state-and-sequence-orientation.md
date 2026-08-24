---
doc_id: hop-adr-0004
title: ADR 0004 - Route state continuity and sequence orientation
intent: Record route-input identity and one molecular sequence orientation convention.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-20
doc_type: decision
---

# ADR 0004: Route state continuity and sequence orientation

## Context

Resolved release and foldback requests can each be valid while describing
unrelated molecules. Bottom-strand products can also be confused with
coordinate-aligned duplex displays if stored direction is implicit.

## Decision

Every molecular sequence field is serialized 5′→3′. Top-coordinate spans are
zero-based and half-open. Bottom-strand products use reverse complement and
their lineage traverses precursor indexes in descending order. A display may
show a coordinate-aligned bottom track 3′→5′, but that transformation is view
state rather than stored molecular state.

A resolved release route is feasible only when its active product sequence is
the foldback precursor sequence. The plan source oligo records the actual route
input: the release precursor when release is present, otherwise the authored
foldback precursor. Ordered route steps must form the declared contiguous state
graph. Foldback and basal pairing are independent branches. Terminal nick
transforms the basal branch before insert assembly consumes it with the
foldback junction and authored payload. Direct synthesis alone requires
source/hairpin-encoding equality.

## Consequences

Disconnected requests produce `HOP-ROUTE-001`. Resolved bundles may include
`source-oligo.fasta` in addition to the distinct generated hairpin encoding.
HOP does not infer a bridge between unrelated sequences.
