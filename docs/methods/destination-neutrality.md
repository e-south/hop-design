# Hairpin-processing method boundary

HOP compiles hairpin designs and bounded sequence transformations. A method
plan records the exact molecules at each step, the events on each strand,
terminal chemistry, pair relationships, covalent joins, primer boundaries, and
the source position of each base, called per-base lineage.
The caller owns protocol conditions, controls, runs, and observations.

## Implemented method

`linear-source-multinick-size-selection-hairpin-pcr@1` derives the following
fixed sequence of molecular states:

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
orientation. The declared length rule must retain exactly one top and one
bottom fragment. Resolution continues only when those fragments satisfy strand
continuity, adapter pairing, both required ligations, and terminal PCR bindings.

Hairpin PCR creates `HairpinPcrDuplex`. A subsequent facing type-IIS digest
creates `RestrictionDigestProduct`, which records two strand products and an
oriented `HairpinEncodingInsert` sequence projection. Each produced cohesive
end records its exact sequence, protruding strand, polarity, aligned span, and
both cut boundaries. Restriction digestion does not create the duplex.

The method compiler requires exact molecular inputs. To assess a degenerate
pool, it would need to report separately whether every member sequence resolves
and whether at least one does.

## Capability facets

| Concern | HOP contract | Boundary |
| --- | --- | --- |
| Design sequence | `HairpinEncodingInsert` | One-dimensional hairpin core; no production-method claim |
| Method availability | `implementation_status` | `available` or `unavailable` for the named HOP version |
| Method input exactness | `input_exactness` | `exact_only` for an implemented exact-sequence request; `not_defined` when no request schema exists |
| Method resolution | `resolution_status` | `not_evaluated`, `complete`, `infeasible`, or `truncated` for one request |
| Physical PCR product | `HairpinPcrDuplex` | Exact complementary strands and derivation through the implemented method |
| Restriction product | `RestrictionDigestProduct` | Destination-neutral strands, exact cohesive ends, union, and encoding projection |
| Assembly input | `AssemblyFragment` | Caller-owned destination, orientation, and compatible ends |
| Experimental result | observation record | Caller-owned execution, controls, yield, and evidence |

The caller checks the product against a destination vector, insertion slot,
orientation, compatible ends, and assembly policy.

`hop_design.methods.list_method_capabilities()` returns these availability and
input-exactness facets for every named method without building or resolving a
request. The returned tuple and its `MethodCapability` records are immutable;
they describe capabilities of that HOP version. The caller selects the method.

## Materials and events

The request declares six sequence materials governed by HOP's material
contract:

1. source oligo;
2. source-PCR forward primer;
3. source-PCR reverse primer;
4. ligation adapter;
5. hairpin-PCR forward primer; and
6. hairpin-PCR reverse primer.

HOP validates the supplied sequences, terminal bindings, and required 5′
phosphates or an explicit kinase preparation. Vector primers remain outside
this handoff because they depend on a destination construct.

`MolecularStrand`, `Fragment`, `StrandPairObservation`, and `CovalentBond`
provide the shared state vocabulary. The compiler constructs the ordered state
plan from the request. Another named method can reuse those records with its
own compiler; callers cannot supply arbitrary reaction sequences.

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

An application owner retains historical lineage, biological meaning, protocol
conditions, selection, and experimental evidence. A generic composition
service may place one immutable annotated HOP product into a larger cassette or
vector and check destination-specific assembly. It must not rederive HOP
fragments, pairings, or features. See [ecosystem ownership](../ecosystem/ownership-boundaries.md).

`compile_linear_source_method_bundle()` turns a complete result into a separate
`MethodBundle`. Its trajectory JSON/SVG, duplex and restriction-product FASTA,
GenBank, and hairpin-encoding projection are derived only from the strict plan.
`load_verified_method_bundle()` recompiles the stored request and requires the
plan and every exported byte to match. This reproduction from saved inputs is
called replay. An infeasible result cannot be written as a complete bundle.

## Completion evidence

The implemented compiler is complete for a request only when:

- every nick and denatured fragment is represented;
- fragment selection is replayable from its declared bounds;
- every pair call uses literal strand bases;
- both ligation bonds use compatible termini;
- PCR primer boundaries derive from the six materials;
- the duplex strands are exact reverse complements; and
- the restriction product and encoding projection replay from facing cuts.

Serialized drift in any of those relationships is rejected. Use the resulting
strand products and cohesive ends for the caller's destination checks.
