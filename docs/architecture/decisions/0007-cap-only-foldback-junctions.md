---
doc_id: hop-adr-0007
title: ADR 0007 - Cap-only foldback junctions
intent: Represent unpaired turns without inventing a retained tract or returning arm.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-20
---

# ADR 0007: Cap-only foldback junctions

## Context

A hairpin can join its payload arms through an unpaired turn without an
additional short stem inside the foldback junction. Requiring at least one
retained and returning nucleotide would force callers to label turn bases as a
physical pair that does not exist.

## Decision

Explicit foldback evaluation accepts a zero-length retained tract and a
zero-length foldback arm when both lengths agree. The junction then contains a
nonempty turn and zero pair observations. Its three spans still form one
contiguous zero-based, half-open partition.

Bounded foldback-arm search continues to require a nonempty retained tract.
There is no arm design space when the paired length is zero, so callers use
explicit evaluation for a cap-only junction.

## Compatibility

This is an additive relaxation of `FoldbackEvaluationRequest`: an input that
previously failed validation can now be evaluated. Existing nonempty foldback
requests, search behavior, diagnostics, plans, and bundle schemas are
unchanged.

## Consequences

HOP can preserve an observed unpaired turn without synthetic base-pair calls.
An empty foldback arm is valid only when the retained tract is also empty; the
existing equal-length and contiguous-partition contracts enforce that rule.
