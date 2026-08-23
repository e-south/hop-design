---
doc_id: hop-processing-and-assembly
title: Processing and assembly
intent: Separate hairpin pairing, molecular processing, ligation evidence, and destination assembly.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
---

# Processing and assembly

HOP describes exact sequence-bearing states and deterministic transitions for
named methods. It does not simulate yield, kinetics, cleanup recovery, PCR side
products, or experimental success.

## Two junctions, different questions

At the closed end, foldback discovery asks whether nicking and release can leave
a tract, turn, and returning arm with the requested pairing geometry.

At the open end, three concerns remain separate:

1. **Basal pairing** classifies the final S3/S2/S1/S0 pairs as M, W, or X.
2. **Basal processing** asks whether release and terminal-nick footprints can
   produce the selected retained scar and derives the surviving strand. The
   later cross-junction route join proves that this is also the released active
   strand.
3. **Assembly-end ligation** asks whether a later cohesive end is acceptable
   under a particular ligase, overhang set, and reaction profile.

A G:T call in the basal stem does not establish that a G:T cohesive end will
ligate efficiently. Bilotti and colleagues found G:T to be the most tolerated
mismatch class across the ligases they tested, while also showing strong
dependence on ligase, sequence, and mismatch position. That result is useful
evidence for caller policy, not a universal HOP acceptance rule. See
[Bilotti et al., 2022](https://doi.org/10.1093/nar/gkac241).

## Implemented method trajectory

The implemented `linear-source-multinick-size-selection-hairpin-pcr@1` method
resolves this closed state sequence:

```text
SourcePcrDuplex
  -> MultiSiteNickedDuplex
  -> DenaturedFragmentSet
  -> LengthSelectedFragmentSet
  -> AdapterAnnealedComplex
  -> LigatedHairpin
  -> HairpinPcrDuplex
  -> RestrictionDigestProduct
```

Every compatible nick site participates in digestion. Selection acts on the
complete fragment set, and later annealing and ligation must consume selected
fragments with continuous lineage and compatible terminal chemistry. Hairpin
PCR creates the duplex; the final Type IIS digest prepares destination-neutral
ends.

This compiler accepts exact molecular inputs. Symbolic payload compilation is
a design capability, not proof that every member of a degenerate pool resolves
through the exact physical trajectory.

## Other production methods

`circular-precursor-exonuclease-selection-multidigest-hairpin-pcr@1` is a named
but unavailable method family. Its identity reserves no permissive schema and
makes no feasibility claim. A real implementation must earn its own typed
materials, states, events, continuity checks, and tests.

An upstream tool may optimize an internal payload junction or a mismatch plan.
That selected plan can become input evidence for a method, but the optimizer is
not itself a circularization trajectory. HOP should not absorb transcription-
factor objectives or application-specific ranking in order to implement the
physical method.

## Handoff to assembly

HOP owns the product and cut geometry it derives. Destination compatibility is
a relation between that product and a caller-supplied destination. The caller
or a generic composition service owns vector placement, orientation, compatible
ends, and the resulting `AssemblyFragment`.

See the [processing method boundary](../processing-method-boundary.md) and
[method-bundle layout](../reference/method-bundle-layout.md) for the strict
contracts.
