# Design language

The design language specifies **the requested hairpin**: its payload, junctions,
and optional paired context. Construction programs and named methods specify
processing steps.

`hop_design.spaces` is the scientist-facing facade for defining, previewing,
and compiling a bounded substrate space. The package root, `hop_design`, is the
specialist design-language surface documented here. The sibling
`hop_design.discovery`, `hop_design.methods`, and `hop_design.views` facades
answer bounded search, named-method, and typed-projection questions. They are
not additional steps in the first-use substrate-space journey.

## Specialist vocabulary

| Term | Meaning |
| --- | --- |
| `Payload` | Caller-authored exact DNA or DNA IUPAC sequence of interest. |
| `FoldbackJunction` | Closed-end retained tract, explicit turn, returning arm, and pair observations. |
| `BasalJunction` | Literal paired open-end arms and their physical pair observations. |
| `PairedStemExtension` | Optional variable-length non-payload paired context. |
| `DesignSpec` | Authored design intent and immutable external references. |
| `DesignDerivation` | Deterministic record of resolved components, with no ordered production chronology. |
| `HairpinEncodingInsert` | Normalized one-dimensional sequence and feature partition encoding the design; it may remain symbolic. |
| `HopBundle` | Content-addressed root manifest; it inventories artifact paths and digests but is not verification evidence. |
| `VerifiedHopBundle` | Spec, plan, provenance, manifest, and immutable artifact bytes admitted only after integrity checks and semantic replay. |

## Authored and derived sequence

The payload is authored once. Its partner is always the DNA IUPAC reverse
complement derived by HOP. Basal junctions and paired stem extensions accept
literal non-payload arms to record their own pairing relationships.

Pair kind is also derived from literal bases:

```text
canonical complement -> watson_crick
G:T or T:G           -> gt_wobble
anything else        -> hard_mismatch
```

Whether an observed pair is acceptable belongs to an explicit policy. Policy
does not rewrite the physical observation.

## Derivation lifecycle

```text
authored intent
    -> semantic validation
    -> derived relationships
    -> evaluated components
    -> ordered feature partition
    -> HairpinEncodingInsert
    -> HopBundle + artifact bytes
    -> persisted design bundle
    -> load_verified_bundle()
    -> VerifiedHopBundle
```

`HopPlan` records deterministic design derivation, not an ordered production
plan. A resolved design may preserve caller-asserted nick or release projection
geometry needed for the encoding. Ordered processing belongs to construction
programs and named method plans.

See [hairpin primitives](hairpin-primitives.md), the
[formal ontology](ontology.md), and [relationships and invariants](relationships-and-invariants.md).
