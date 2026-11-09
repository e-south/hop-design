# Linear-source hairpin-PCR materials

`linear-source-multinick-size-selection-hairpin-pcr@1` consumes six
vendor-neutral sequence materials: the source oligo, its two PCR primers, a
ligation adapter and the two hairpin-PCR primers. The material resolver checks
where each primer binds at the source or adapter termini before the method
compiler derives physical states.

```python
# Resolve the method with its explicit oligos and terminal chemistry.
import hop_design.methods as methods

phosphate = (methods.OligoModification.FIVE_PRIME_PHOSPHATE,)
spec = methods.LinearSourceHairpinPcrMaterialsSpec(
    method_id="linear-source-demo",
    source_oligo=methods.ProcessOligo(
        material_id="source",
        sequence="ACGTACGTNNRYGCTTAG",
    ),
    source_pcr_forward_primer=methods.ProcessOligo(
        material_id="source-fwd",
        sequence="ACGTAC",
    ),
    source_pcr_reverse_primer=methods.ProcessOligo(
        material_id="source-rev",
        sequence="CTAAGC",
        modifications=phosphate,
    ),
    ligation_adapter=methods.ProcessOligo(
        material_id="adapter",
        sequence="TTGACCGTAACC",
        modifications=phosphate,
    ),
    hairpin_pcr_forward_primer=methods.ProcessOligo(
        material_id="hairpin-fwd",
        sequence="ACGTACGT",
    ),
    hairpin_pcr_reverse_primer=methods.ProcessOligo(
        material_id="hairpin-rev",
        sequence="GGTTACGG",
    ),
    ligation_end_preparation=(methods.LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS),
)

plan = methods.resolve_linear_source_hairpin_pcr_materials(spec)
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

Supply vector primers, destination overhangs, and larger construct context in
the caller's assembly plan; they depend on that target.
