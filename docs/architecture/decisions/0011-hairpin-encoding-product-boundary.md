---
doc_id: hop-adr-0011
title: ADR 0011 - Typed hairpin-encoding product boundary
intent: Define HOP's current product and the persisted consumer seam without claiming an unmodeled physical duplex.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-21
---

# ADR 0011: Typed hairpin-encoding product boundary

## Context

`HopPlan` previously exposed a generic `final_insert` sequence and separate
top-level features. The name could be read as a physical PCR duplex or a
destination-ready cloning fragment. Neither interpretation was supported by
the model: the plan did not encode the adapter-annealed, ligated-hairpin, or
hairpin-PCR states, and callers could reconstruct the features independently.

## Decision

`hop.plan/v2` replaces that surface with one `HairpinEncodingInsert`. It owns
the one-dimensional sequence, its SHA-256 digest, and the ordered nested
features that exactly partition it. The bundle artifact is
`hairpin-encoding.fasta`.

`load_verified_bundle()` is the public persisted-consumer boundary. It returns
the typed spec, plan, provenance, manifest, and immutable artifacts only after
content verification and deterministic spec-to-plan replay.

There is no v1 reader, field alias, fallback artifact name, or compatibility
shim. Alpha consumers must migrate deliberately.

## Consequences

HOP can hand downstream systems one immutable annotated product without asking
them to rederive foldback, paired-payload, stem-extension, or basal spans.
`HairpinEncodingInsert` remains a sequence representation, not a physical
duplex and not evidence of cloning readiness.

The name `LinearHairpinPcrDuplex` is reserved for a future typed endpoint that
must be derived from explicit annealing, ligation, and PCR transitions. FASTA,
feature, and GenBank exports for that physical product remain blocked until the
state exists. Destination-specific `AssemblyFragment` objects remain caller
owned.
