# Design language

The design language specifies **the requested hairpin**: its payload, junctions,
and optional paired context. Construction programs and named methods specify
processing steps. To discover complete preparations from a supplied stem, start
with `hop_design.construction` and the [design discovery guide](../guides/discover-designs.md).
This page explains the sequence anatomy used within those preparations and by
the specialist design operations below.

Use `hop_design.spaces` to define a finite set of permitted sequences, preview
its size, and compile its members. That set is a **substrate space**. The package
root, `hop_design`, provides the specialist design-language operations documented
here. Use `hop_design.discovery` for bounded search, `hop_design.methods` for
named production methods, and `hop_design.views` to inspect already-derived
states. These separate interfaces are not additional steps in the first-use
substrate-space journey.

## Specialist vocabulary

| Term | Meaning |
| --- | --- |
| `Payload` | Caller-authored exact DNA or DNA IUPAC sequence of interest. |
| `FoldbackJunction` | Closed-end retained tract, explicit turn, returning arm, and pair observations. |
| `BasalJunction` | Literal paired open-end arms and their physical pair observations. |
| `PairedStemExtension` | Optional variable-length non-payload paired context. |
| `DesignSpec` | Authored design intent and immutable external references. |
| `DesignDerivation` | Reproducible account of how components were resolved; it does not order production steps. |
| `HairpinEncodingInsert` | Normalized one-dimensional sequence and feature partition encoding the design; it may remain symbolic. |
| `HopBundle` | Root manifest listing artifact paths and content digests; its identifier is derived from its contents, but it is not verification evidence. |
| `VerifiedHopBundle` | Spec, plan, provenance, manifest, and immutable artifact bytes accepted only after checking their integrity and reproducing them from the stored inputs. |

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

`HopPlan` records how HOP derived the design. Its order does not describe
production steps. A resolved design may preserve caller-supplied nick or release
geometry needed to derive the encoding. Construction programs and named method
plans record ordered processing.

See [hairpin primitives](hairpin-primitives.md), the
[formal ontology](ontology.md), and [relationships and invariants](relationships-and-invariants.md).
