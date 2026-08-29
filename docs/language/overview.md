---
doc_id: hop-design-language-overview
title: Design language
intent: Introduce the specialist vocabulary for declaring and compiling one hairpin design.
audience:
  - users
  - integrators
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-29
doc_type: explanation
journey:
  - compile
---

# Design language

The design language answers one question: **what hairpin is being requested?**
It is declarative. It does not claim how the hairpin will be produced.

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
complement derived by HOP. Literal non-payload arms remain possible in basal
junctions and paired stem extensions because those objects answer different
structural questions.

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
geometry needed for the encoding. Named molecular chronology belongs only to a
method plan.

See [hairpin primitives](hairpin-primitives.md), the
[formal ontology](ontology.md), and [relationships and invariants](relationships-and-invariants.md).
