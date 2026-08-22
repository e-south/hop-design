---
doc_id: hop-linear-source-method-materials
title: Linear-source hairpin-PCR materials
intent: Explain the six-oligo input, terminal checks, and ownership boundary for the linear-source method.
audience:
  - users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
---

# Linear-source hairpin-PCR materials

`linear-source-multinick-size-selection-hairpin-pcr@1` consumes six
vendor-neutral sequence materials. The material resolver checks terminal
relationships before the method compiler derives physical states.

```python
import hop_design as hop

phosphate = (hop.OligoModification.FIVE_PRIME_PHOSPHATE,)
spec = hop.LinearSourceHairpinPcrMaterialsSpec(
    method_id="linear-source-demo",
    source_oligo=hop.ProcessOligo(
        material_id="source",
        sequence="ACGTACGTNNRYGCTTAG",
    ),
    source_pcr_forward_primer=hop.ProcessOligo(
        material_id="source-fwd",
        sequence="ACGTAC",
    ),
    source_pcr_reverse_primer=hop.ProcessOligo(
        material_id="source-rev",
        sequence="CTAAGC",
        modifications=phosphate,
    ),
    ligation_adapter=hop.ProcessOligo(
        material_id="adapter",
        sequence="TTGACCGTAACC",
        modifications=phosphate,
    ),
    hairpin_pcr_forward_primer=hop.ProcessOligo(
        material_id="hairpin-fwd",
        sequence="ACGTACGT",
    ),
    hairpin_pcr_reverse_primer=hop.ProcessOligo(
        material_id="hairpin-rev",
        sequence="GGTTACGG",
    ),
    ligation_end_preparation=hop.LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS,
)

plan = hop.resolve_linear_source_hairpin_pcr_materials(spec)
```

The source oligo accepts DNA IUPAC symbols at the material-validation stage so
a pool can retain controlled degeneracy. A physical method request requires an
exact source sequence because cut sites, fragments, bonds, and PCR products
must resolve to literal bases. Primers and the adapter always require exact
DNA. Material IDs are unique.

The plan schema is `hop.linear-source-hairpin-pcr-materials-plan/v1`. It records:

- the source-PCR forward primer on the source prefix;
- the source-PCR reverse primer on the source suffix by reverse complement;
- the hairpin-PCR forward primer on the source prefix; and
- the hairpin-PCR reverse primer on the adapter suffix by reverse complement.

Pre-phosphorylated input requires a 5′ phosphate on the source-PCR reverse
primer and ligation adapter. `kinase_step` records that those ligatable ends are
prepared during the method instead.

Vector primers, destination overhangs, and larger construct context remain
caller-owned because they depend on the assembly target rather than hairpin
processing.
