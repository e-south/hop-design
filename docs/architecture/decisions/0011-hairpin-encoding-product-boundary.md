# ADR 0011: Typed hairpin-encoding product boundary

Updated by [ADR 0020](0020-separate-design-derivation-from-method-chronology.md).

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
`HairpinEncodingInsert` represents one annotated sequence.

`HairpinPcrDuplex` is the distinct typed endpoint derived from explicit
annealing, ligation, and PCR transitions. FASTA, feature, and GenBank exports
for that physical product must consume the method plan rather than infer a
duplex from `HairpinEncodingInsert`. Destination-specific `AssemblyFragment`
objects remain caller owned.
