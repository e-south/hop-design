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

`HopBundle` and `MethodBundle` are separate bundle types. Their shared
hairpin-encoding digest lets a caller check that they describe the same encoding.
The bundles retain separate identities. Destination vector, orientation,
compatible assembly ends, and experimental evidence remain downstream.

## Consequences

A design can remain valid while one method is infeasible or unavailable. More
than one method may later produce the same design without changing its design
bundle. Consumers that need duplex or restriction-product states must verify the method
bundle explicitly; those states are absent from a design bundle.
