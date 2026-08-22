---
doc_id: hop-processing-method-boundary
title: Hairpin-processing method boundary
intent: Define HOP's implemented molecular transformations without absorbing laboratory execution or destination assembly.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
---

# Hairpin-processing method boundary

HOP compiles hairpin designs and bounded sequence transformations. It is not a
general reaction simulator. A method plan records sequence-bearing states,
strand-specific events, terminal chemistry, pair relationships, covalent joins,
primer boundaries, and per-base lineage. Laboratory conditions, recovery,
controls, runs, and observations remain with the caller.

## Implemented method

`linear-source-multinick-size-selection-hairpin-pcr@1` has this closed state
sequence:

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

The request supplies six sequence materials, one or more nicking agents, an
inclusive fragment-length rule, an adapter-pairing span and mismatch bounds,
one type-IIS restriction agent, and an optional expected hairpin encoding. HOP
scans the complete source for every compatible nick site. It does not select a
site by ordinal position or record ID.

After nicking, HOP enumerates every top- and bottom-strand fragment in 5′→3′
orientation. Length selection is a declared deterministic rule, not an
empirical recovery prediction. Resolution continues only when the rule retains
one top and one bottom fragment that satisfy strand continuity, adapter pairing,
both required ligations, and terminal PCR bindings.

Hairpin PCR creates `HairpinPcrDuplex`. A subsequent facing type-IIS digest
creates `RestrictionDigestProduct`, which records two strand products and an
oriented `HairpinEncodingInsert` sequence projection. Restriction digestion does
not create the duplex.

## Capability facets

| Concern | HOP contract | Boundary |
| --- | --- | --- |
| Design sequence | `HairpinEncodingInsert` | One-dimensional hairpin core; no production-method claim |
| Method availability | `implementation_status` | `available` or `unavailable` for the named HOP version |
| Method resolution | `resolution_status` | `not_evaluated`, `complete`, `infeasible`, or `truncated` for one request |
| Physical PCR product | `HairpinPcrDuplex` | Exact complementary strands and derivation through the implemented method |
| Restriction product | `RestrictionDigestProduct` | Destination-neutral strands, cuts, union, and encoding projection |
| Assembly input | `AssemblyFragment` | Caller-owned destination, orientation, and compatible ends |
| Experimental result | observation record | Caller-owned execution, controls, yield, and evidence |

No HOP product is called cloning-ready without a destination vector, insertion
slot, orientation, compatible ends, and assembly policy.

## Materials and events

The six HOP-owned sequence materials are:

1. source oligo;
2. source-PCR forward primer;
3. source-PCR reverse primer;
4. ligation adapter;
5. hairpin-PCR forward primer; and
6. hairpin-PCR reverse primer.

HOP validates terminal bindings and required 5′ phosphates or an explicit
kinase preparation. Vector primers remain outside this handoff because they
depend on a destination construct.

`MolecularStrand`, `Fragment`, `StrandPairObservation`, and `CovalentBond`
provide the shared state vocabulary. The compiler, not the caller, constructs
the ordered state plan. This preserves an extension seam for another named
method without exposing an unrestricted reaction language.

## Other production methods

`circular-precursor-exonuclease-selection-multidigest-hairpin-pcr@1` is a
separate named method family. HOP currently reports it as `unavailable` and
`not_evaluated`; no empty request class or permissive payload partner field is
present.

A sequence that needs noncomplementary payload partners can be authoritative
while remaining infeasible for the linear-source method. The reverse-complement
payload invariant is therefore unchanged. Another production method must earn
its own inputs, states, continuity checks, and tests.

## Consumer handoff

Research Studies owns Retron identity, historical lineage, biological meaning,
protocol conditions, selection, and experimental evidence. Construct may place
one immutable annotated HOP product into a larger cassette or vector and check
destination-specific assembly. It must not rederive HOP fragments, pairings, or
features.

`compile_linear_source_method_bundle()` turns a complete result into a separate
`MethodBundle`. Its trajectory JSON/SVG, duplex and restriction-product FASTA,
GenBank, and hairpin-encoding projection are derived only from the strict plan.
`load_verified_method_bundle()` recompiles the stored request and requires the
plan and every exported byte to match. An infeasible result cannot be written
as a complete bundle.

## Completion evidence

The implemented compiler is complete for a request only when:

- every nick and denatured fragment is represented;
- fragment selection is replayable from its declared bounds;
- every pair call uses literal strand bases;
- both ligation bonds use compatible termini;
- PCR primer boundaries derive from the six materials;
- the duplex strands are exact reverse complements; and
- the restriction product and encoding projection replay from facing cuts.

Serialized drift in any of those relationships is rejected. This evidence does
not establish laboratory yield or destination compatibility.
