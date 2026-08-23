---
doc_id: hop-adr-0013
title: ADR 0013 - Separate replayable method bundles
intent: Keep production-method evidence distinct from hairpin-design identity.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
doc_type: decision
---

# ADR 0013: Separate replayable method bundles

## Context

`HopBundle` records a design specification, compiled plan, and
hairpin-encoding product. The linear-source compiler now also owns a complete
sequence of physical states through PCR and restriction processing. Adding
those states to every design bundle would imply one production method per
design and would couple design identity to method availability.

## Decision

HOP uses a separate `MethodBundle` for one complete method request. Its root
manifest records the request, method kind, compiler version, plan and request
digests, exact hairpin-encoding sequence digest, and every generated artifact.

The current method bundle contains the strict request and plan, typed
trajectory JSON, deterministic SVG, duplex and restriction-product FASTA,
GenBank, and the hairpin-encoding projection. Writers validate paths before any
artifact is written, publish atomically, and never replace an existing path.
Loaders verify content integrity and then recompile the stored request. The
replayed plan, artifact bytes, and manifest must match.

`HopBundle` and `MethodBundle` are sibling consumer boundaries. A shared
hairpin-encoding digest is a typed join, not shared identity. Destination
vector, orientation, compatible assembly ends, and experimental evidence remain
downstream.

## Consequences

A design can remain valid while one method is infeasible or unavailable. More
than one method may later produce the same design without changing its design
bundle. Consumers that need physical-method evidence must verify the method
bundle explicitly; a design bundle alone does not establish a duplex or
restriction product.
