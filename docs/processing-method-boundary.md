---
doc_id: hop-processing-method-boundary
title: Hairpin-processing method boundary
intent: Ground HOP in one concrete processing method without importing application-specific biology or laboratory execution.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-21
---

# Hairpin-processing method boundary

HOP is a sequence-design compiler for a specific family of hairpin-processing
methods. It is not a universal reaction simulator. Its initial method scope is
the path from an authored single-stranded sequence to a checked hairpin design
and a linear double-stranded insert with inverted repeats.

The reference method has this molecular spine:

```text
source ssDNA
  -> precursor duplex
  -> nicked and released ssDNA fragment
  -> adapter-annealed intermediate
  -> ligated ssDNA hairpin
  -> hairpin-PCR duplex
  -> linear dsDNA insert with inverted repeats
```

This sequence is a boundary model, not an executable laboratory recipe. HOP
may record the sequence-bearing states, transformations, coordinate lineage,
and route-required oligos needed to explain a design. It does not prescribe
reaction volumes, incubation conditions, cleanup choices, cycle counts,
controls, or experimental acceptance.

## Current and target coverage

| Method concern | Current public contract | Remaining contract work |
| --- | --- | --- |
| Input sequence and paired arm | Exact and DNA IUPAC payloads; paired arm derived by reverse complement | None for the current compiler path |
| Foldback and basal geometry | Typed junctions, pair calls, spans, diagnostics, and route-neutral component assembly | Predecessor candidate and ordering parity |
| Nicking and duplex release | Explicit nick/cut geometry and released-strand lineage | Joint route discovery and sequence-level route candidates |
| Adapter annealing and ligation | Source and adapter materials, terminal binding, and ligation-end preparation are represented | Typed annealed and ligated states with continuity checks |
| Hairpin PCR and inverted-repeat duplex | Final insert and both hairpin-PCR primer bindings are represented; the PCR transition is not | A bounded method-plan transition from ligated hairpin to duplex |
| Larger construct or vector placement | Outside HOP | Caller-owned composition or assembly handoff |
| Secondary-structure prediction | Optional consumer of plan-owned sequence artifacts | Prove an interoperable adapter before defining a plugin protocol |

The current `resolved_events` graph therefore establishes junction and release
mechanics, not end-to-end method coverage. A verified bundle proves that its
software contracts replay; it does not prove that the laboratory method works.

## Four different kinds of information

The method contract must keep these categories separate:

- A **molecular state** is a sequence-bearing object at one point in the
  method, such as a precursor duplex, released strand, ligated hairpin, or
  linear insert.
- A **process event** transforms declared input states into declared output
  states, such as duplex release, annealing, ligation, or amplification.
- A **process material** is an oligo required by a generic method event, such
  as a source oligo, adapter, or primer. It is not a transient molecular state.
- An **observation** records what happened in an experiment. Runs, controls,
  gels, yields, and acceptance decisions remain with the caller.

Every event must name its input and output states. Every route-required
material must name the event that consumes it and the sequence derivation that
produced it. Missing derivation evidence fails closed; HOP does not infer an
orderable primer from a diagram or label.

Hairpin-path materials belong to HOP only when the generic method cannot be
executed without them. Primers or flanks that add a plasmid, assay, barcode, or
other application context belong to the caller.

The first material contract covers the source oligo, two source-PCR primers,
ligation adapter, and two hairpin-PCR primers. It verifies terminal binding and
records whether ligatable 5′ phosphates are supplied or produced by a kinase
step. Vector primers remain outside that six-material handoff.

## Supplied and discovered designs

A foldback or basal component does not need to have been found by a HOP search.
Users may supply a hand-designed, inherited, or previously tested component
and compile it through `component_assembly`. HOP validates its sequence,
topology, pairing, and composition without claiming an enzyme route or a
discovery history.

Supplied designs must still fit the declared molecular contract. An additional
paired stem segment, intentional internal mismatch, or other sequence-bearing
context must be modeled explicitly; it cannot be hidden inside the payload or
an annotation. The paired payload remains derived by reverse complement.

Discovery and supply are provenance paths, not different molecular kinds:

```text
bounded discovery ----+
                      +--> selected components --> checked HOP plan
caller-supplied ------+
```

Application identifiers, parentage, experimental rationale, and performance
remain in the caller's record and may be linked through neutral external
references. When a route is unknown, the plan records no route assertion; it
does not invent a nicked strand, processing agent, or feasibility result.

## Composition and assessment seams

HOP owns the hairpin-specific order, derivation, spans, and method state. A
generic sequence-composition service may consume that plan to add larger
context and write GenBank, FASTA, feature, folding, or review artifacts. HOP
does not need to reimplement those generic services.

Likewise, a secondary-structure predictor consumes a selected HOP sequence and
returns an advisory artifact linked to the plan or bundle digest. It cannot
change molecular validity. A formal plugin registry is deferred until at least
two independent integrations establish the same stable contract.

## Initial completion test

The initial method scope is complete when one sanitized example proves:

1. every sequence-bearing state from source ssDNA through the linear insert;
2. continuity across nicking, release, annealing, ligation, and hairpin PCR;
3. exact, oriented, route-required oligos with consuming-step links;
4. separation of the HOP insert from caller-added construct context; and
5. deterministic molecular-state and review artifacts derived from one plan.

This completion test does not require a universal reaction language, a
workspace system, laboratory automation, or a built-in structure predictor.
