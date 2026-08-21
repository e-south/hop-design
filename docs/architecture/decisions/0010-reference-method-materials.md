---
doc_id: hop-adr-0010
title: ADR 0010 - Reference method materials
intent: Define the first vendor-neutral oligo handoff for the reference hairpin-processing method.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-21
---

# ADR 0010: Reference method materials

## Context

A checked insert sequence is not the complete handoff for the reference method.
The path also requires a source oligo, two primers for source amplification, a
ligation adapter, and two primers for hairpin amplification. These are sequence
materials consumed by generic method events. Vector primers and cloning context
belong to the downstream construct.

## Decision

`HairpinMethodMaterialsSpec` records exactly six vendor-neutral oligos:

1. source oligo;
2. source-PCR forward primer;
3. source-PCR reverse primer;
4. ligation adapter;
5. hairpin-PCR forward primer; and
6. hairpin-PCR reverse primer.

`resolve_hairpin_method_materials` verifies four terminal binding
relationships. Forward primers match the source prefix. Reverse primers bind
the source or adapter suffix by reverse complement. The returned plan records
the oriented zero-based half-open binding spans and rejects serialized drift.

Ligation-end preparation is explicit. `pre_phosphorylated_oligos` requires a
5′ phosphate on the source-PCR reverse primer and ligation adapter.
`kinase_step` records that the terminal chemistry is produced during the
method instead.

## Boundary

The contract describes sequences, terminal modifications, and binding
relationships. It does not prescribe reaction volumes, enzymes, temperatures,
cycle counts, cleanup methods, controls, procurement fields, or laboratory
acceptance. Primers that amplify a plasmid or add application-specific assembly
context remain caller-owned.

## Compatibility

The material spec and plan use new, independent schema identifiers. They do
not change `HopSpec`, `HopPlan`, or bundle replay. Linking these materials into
the end-to-end molecular-state graph remains a later schema decision after the
annealed and ligated state sequences are proven.
