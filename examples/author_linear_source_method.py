"""Author, compile, write, and verify one explicit linear-source method request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hop_design as hop
import hop_design.methods as methods

SOURCE = "ATGCATCACGAGTTAACCCACGAGAGGTCTCACGAGGATACCGTTAAGCTCGATTACCTCAGCAATTGCG"
ADAPTER = "TTGTGAGACCTCTTGTGACGTTAGCCTAGTCCGATA"
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


def build_request() -> methods.LinearSourceMultinickHairpinPcrRequest:
    """Construct every material and processing input without hidden defaults."""
    materials = methods.LinearSourceHairpinPcrMaterialsSpec(
        schema="hop.linear-source-hairpin-pcr-materials/v1",
        method_id="synthetic-multinick",
        source_oligo=_oligo("source", SOURCE),
        source_pcr_forward_primer=_oligo("source-fwd", SOURCE[:14]),
        source_pcr_reverse_primer=_oligo(
            "source-rev",
            "CGCAATTGCTGAGG",
            phosphorylated=True,
        ),
        ligation_adapter=_oligo("adapter", ADAPTER, phosphorylated=True),
        hairpin_pcr_forward_primer=_oligo("hairpin-fwd", SOURCE[:19]),
        hairpin_pcr_reverse_primer=_oligo(
            "hairpin-rev",
            "TATCGGACTAGGCTAACGTC",
        ),
        ligation_end_preparation=(methods.LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS),
    )
    nicking_agents = (
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
    )
    selection = methods.FragmentLengthSelection(min_length_nt=16)
    adapter_annealing = methods.AdapterAnnealingRequest(
        adapter_span=hop.Span(
            start=hop.Boundary(offset=0),
            end=hop.Boundary(offset=17),
        ),
        max_gt_wobbles=2,
        max_hard_mismatches=0,
    )
    restriction_agent = hop.ReleaseAgent(
        agent_id="example:release-agent/type-iis@1",
        motif_top_5to3="GGTCTC",
        top_cut_offset=7,
        bottom_cut_offset=11,
        warning_codes=(),
    )
    return methods.LinearSourceMultinickHairpinPcrRequest(
        schema="hop.linear-source-multinick-hairpin-pcr-request/v1",
        request_id="example:method-request/readable-synthetic-multinick@1",
        method_kind="linear-source-multinick-size-selection-hairpin-pcr@1",
        materials=materials,
        nicking_agents=nicking_agents,
        fragment_selection=selection,
        adapter_annealing=adapter_annealing,
        restriction_agent=restriction_agent,
        hairpin_encoding_projection_orientation=(
            methods.BindingOrientation.REVERSE_COMPLEMENT_5TO3
        ),
        expected_hairpin_encoding=HAIRPIN_ENCODING,
    )


def main() -> None:
    """Compile the authored request and report the replay-verified result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    request = build_request()
    compilation = methods.compile_linear_source_method_bundle(request)
    compilation.write(args.out)
    verified = methods.load_verified_method_bundle(args.out)
    plan = verified.plan
    product = plan.restriction_digest_product

    print(
        json.dumps(
            {
                "method_bundle_verified": True,
                "method_bundle_id": verified.bundle.bundle_id,
                "method_kind": plan.method_kind,
                "material_count": len(plan.materials.materials),
                "nicking_agent_count": len(request.nicking_agents),
                "selected_fragment_count": len(
                    plan.length_selected_fragment_set.retained_fragment_ids
                ),
                "cohesive_end_count": len(product.cohesive_ends),
                "destination_readiness": product.destination_readiness,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
