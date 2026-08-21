---
doc_id: hop-method-materials
title: Reference method materials
intent: Explain the public oligo-material input, validation, and ownership boundary.
audience:
  - users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-21
---

# Reference method materials

The reference hairpin path requires six sequence materials. HOP validates their
terminal relationships without modeling a complete PCR or ligation reaction.

```python
import hop_design as hop

phosphate = (hop.OligoModification.FIVE_PRIME_PHOSPHATE,)
spec = hop.HairpinMethodMaterialsSpec(
    method_id="example-method",
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
    ligation_end_preparation=(hop.LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS),
)

plan = hop.resolve_hairpin_method_materials(spec)
```

The source oligo accepts DNA IUPAC symbols so a pool can retain controlled
degeneracy. Primers and the ligation adapter require exact DNA. Material IDs
must be unique.

The plan uses schema `hop.hairpin-method-materials-plan/v1`. It preserves the
six materials, required terminal chemistry, and four bindings:

- source-PCR forward primer to the source prefix;
- source-PCR reverse primer to the source suffix by reverse complement;
- hairpin-PCR forward primer to the source prefix; and
- hairpin-PCR reverse primer to the adapter suffix by reverse complement.

The contract stops before vector amplification and larger construct assembly.
Those materials depend on the destination construct and belong to the caller.
