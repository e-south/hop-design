"""Sanitized linear-source method request shared across contract tests."""

from __future__ import annotations

import hop_design as hop
import hop_design.methods as methods

SOURCE = "ATGCATCACGAGTTAACCCACGAGAGGTCTCACGAGGATACCGTTAAGCTCGATTACCTCAGCAATTGCG"
ADAPTER = "TTGTGAGACCTCTTGTGACGTTAGCCTAGTCCGATA"
LIGATED = (
    "ATGCATCACGAGTTAACCCACGAGAGGTCTCACGAGGATACCGTTAAGCTCGATTACC"
    "CGCAATTGCTGAGGTAATCGAGCTTAACGGTATCC"
    "TTGTGAGACCTCTTGTGACGTTAGCCTAGTCCGATA"
)
HAIRPIN_ENCODING = "CAAGGATACCGTTAAGCTCGATTACCTCAGCAATTGCGGGTAATCGAGCTTAACGGTATCCTCG"


def _oligo(
    material_id: str,
    sequence: str,
    *,
    phosphorylated: bool = False,
) -> methods.ProcessOligo:
    modifications = (methods.OligoModification.FIVE_PRIME_PHOSPHATE,) if phosphorylated else ()
    return methods.ProcessOligo(
        material_id=material_id,
        sequence=sequence,
        modifications=modifications,
    )


def linear_source_method_request(
    *,
    min_length_nt: int = 16,
    kinase_step: bool = False,
) -> methods.LinearSourceMultinickHairpinPcrRequest:
    """Return one neutral complete route with repeated nicking sites."""
    materials = methods.LinearSourceHairpinPcrMaterialsSpec(
        schema="hop.linear-source-hairpin-pcr-materials/v1",
        method_id="synthetic-multinick",
        source_oligo=_oligo("source", SOURCE),
        source_pcr_forward_primer=_oligo("source-fwd", SOURCE[:14]),
        source_pcr_reverse_primer=_oligo(
            "source-rev",
            "CGCAATTGCTGAGG",
            phosphorylated=not kinase_step,
        ),
        ligation_adapter=_oligo("adapter", ADAPTER, phosphorylated=not kinase_step),
        hairpin_pcr_forward_primer=_oligo("hairpin-fwd", SOURCE[:19]),
        hairpin_pcr_reverse_primer=_oligo("hairpin-rev", "TATCGGACTAGGCTAACGTC"),
        ligation_end_preparation=(
            methods.LigationEndPreparation.KINASE_STEP
            if kinase_step
            else methods.LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS
        ),
    )
    return methods.LinearSourceMultinickHairpinPcrRequest(
        schema="hop.linear-source-multinick-hairpin-pcr-request/v1",
        request_id="example:method-request/synthetic-multinick@1",
        materials=materials,
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/bottom-repeat@1",
                motif_top_5to3="CACGAG",
                nicked_strand=hop.Strand.BOTTOM,
                cut_offset=5,
                warning_codes=(),
            ),
            hop.NickingAgent(
                agent_id="example:nicking-agent/top-terminal@1",
                motif_top_5to3="CCTCAGC",
                nicked_strand=hop.Strand.TOP,
                cut_offset=2,
                warning_codes=(),
            ),
        ),
        fragment_selection=methods.FragmentLengthSelection(min_length_nt=min_length_nt),
        adapter_annealing=methods.AdapterAnnealingRequest(
            adapter_span=hop.Span(
                start=hop.Boundary(offset=0),
                end=hop.Boundary(offset=17),
            ),
            max_gt_wobbles=2,
            max_hard_mismatches=0,
        ),
        restriction_agent=hop.ReleaseAgent(
            agent_id="example:release-agent/type-iis@1",
            motif_top_5to3="GGTCTC",
            top_cut_offset=7,
            bottom_cut_offset=11,
            warning_codes=(),
        ),
        expected_hairpin_encoding=HAIRPIN_ENCODING,
    )


__all__ = [
    "ADAPTER",
    "HAIRPIN_ENCODING",
    "LIGATED",
    "SOURCE",
    "linear_source_method_request",
]
