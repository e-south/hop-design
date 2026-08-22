---
doc_id: hop-adr-0010
title: ADR 0010 - Linear-source hairpin-PCR materials
intent: Define the vendor-neutral oligo handoff for the linear-source multi-nick method.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
---

# ADR 0010: Linear-source hairpin-PCR materials

## Context

A checked hairpin-encoding sequence does not describe how the linear-source
method produces it. The transformation also consumes a source oligo, two
source-PCR primers, a ligation adapter, and two hairpin-PCR primers. Vector
primers and destination context serve a later assembly operation.

## Decision

`LinearSourceHairpinPcrMaterialsSpec` records exactly six vendor-neutral oligos:

1. source oligo;
2. source-PCR forward primer;
3. source-PCR reverse primer;
4. ligation adapter;
5. hairpin-PCR forward primer; and
6. hairpin-PCR reverse primer.

`resolve_linear_source_hairpin_pcr_materials` verifies four terminal binding
relationships. Forward primers match the source prefix. Reverse primers bind
the source or adapter suffix by reverse complement. The returned plan records
oriented zero-based half-open spans and rejects serialized drift.

Ligation-end preparation is explicit. `pre_phosphorylated_oligos` requires a
5′ phosphate on the source-PCR reverse primer and ligation adapter.
`kinase_step` records that the method prepares those termini before ligation.

## Boundary

The contract describes sequences, terminal modifications, and binding
relationships. Reaction volumes, temperatures, cycle counts, cleanup product
names, controls, procurement fields, and laboratory acceptance remain outside
the contract. Primers that amplify a vector or add destination-specific ends
remain caller-owned.

## Consequences

The material schemas use transformation-specific identifiers. Retired generic
names are not accepted. Method materials now feed the explicit multi-nick,
selection, annealing, ligation, and PCR state plan; they are not a parallel
handoff detached from the physical derivation.
