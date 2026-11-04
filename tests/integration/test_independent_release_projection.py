"""Retained insert boundaries are independent of the paired hairpin core."""

from hop_design.design.construction.projections.navigation import _project_accepted_route
from tests.integration.test_complete_construction_clone import _clone_request
from tests.integration.test_complete_construction_discovery import _discover_raw


def test_release_can_trim_outer_core_without_trimming_payload_or_association_record(tmp_path):
    from hop_design import construction
    from hop_design.design.bundle import load_verified_bundle
    from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
    from hop_design.models.construction.complete import (
        PcrPrimer,
        ReleaseSideRequirement,
        TypeIisReleaseRequest,
    )
    from hop_design.models.molecular_state import StrandEnd
    from hop_design.models.physical import SiteOrientation
    from tests.contract.test_basal_construction_discovery import _provisioning, _type_iis
    from tests.integration.test_complete_construction_clone import _clone_basal_result
    from tests.integration.test_complete_construction_discovery import (
        _construction_request,
        _material,
    )
    from tests.integration.test_complete_construction_pcr import _foldback, _payload

    payload = _payload()
    foldback = _foldback(payload)
    basal = _clone_basal_result(
        payload,
        pairing_allowances=(BasalPairAllowance.MATCH,) * 4 + (BasalPairAllowance.ANY,) * 2,
        nickase_pattern="TTTTTT",
        requested_overhang="AAAA",
        payload_end_offset_bp=0,
    )
    selected = next(
        item for item in basal.realizations if item.proximal_adapter_sequence == "TTTTGA"
    )
    fp, bp = tmp_path / "foldback.json", tmp_path / "basal.json"
    fp.write_text(foldback.model_dump_json(by_alias=True))
    bp.write_text(basal.model_dump_json(by_alias=True))
    compiled = construction.compile_design_from_local_realizations(
        design_id="trim-outer-core",
        payload_sequence=payload.payload.sequence,
        endpoint="clone_ready_duplex",
        foldback=construction.load_verified_local_neighborhood(fp),
        foldback_realization_id=foldback.realizations[0].foldback_realization_id,
        basal=construction.load_verified_local_neighborhood(bp),
        basal_realization_id=selected.basal_realization_id,
    )
    design = load_verified_bundle(compiled.write(tmp_path / "design"))
    # The paired core describes six source-adapter contacts, irrespective of
    # how many of their bases a later digest retains in the released insert.
    assert design.plan.hairpin_encoding_insert.sequence.startswith("AAAAAAGACA")
    assert design.plan.hairpin_encoding_insert.sequence.endswith("TGTCTTTTGA")
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        adapter=_material("ligation-adapter", "TTTTGAGACC"),
        forward_primer=PcrPrimer(
            oligo=_material("forward-primer", "GGTCTCAAAA"), annealing_length_nt=4
        ),
        reverse_primer=PcrPrimer(oligo=_material("reverse-primer", "GGTC"), annealing_length_nt=4),
        release=TypeIisReleaseRequest(
            enzyme_provisioning=_provisioning(_type_iis(), max_operations=2),
            left=ReleaseSideRequirement(
                orientation=SiteOrientation.FORWARD,
                cohesive_end_sequence="AAAA",
                overhang_end=StrandEnd.FIVE_PRIME,
                payload_end_offset_bp=2,
            ),
            right=ReleaseSideRequirement(
                orientation=SiteOrientation.REVERSE,
                cohesive_end_sequence="AAAA",
                overhang_end=StrandEnd.FIVE_PRIME,
                payload_end_offset_bp=0,
            ),
            max_site_pairs=16,
        ),
    ).model_copy(
        update={
            "selected_basal_realization_id": selected.basal_realization_id,
            "selected_foldback_realization_id": foldback.realizations[0].foldback_realization_id,
        }
    )
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    assert len(result.realizations) == 1, result.failure_reasons
    realized = result.realizations[0]
    evidence = realized.final_product.release_evidence
    assert (
        evidence.design_parent_projection.sequence == design.plan.hairpin_encoding_insert.sequence
    )
    assert (
        evidence.released_union_projection.sequence
        == evidence.design_parent_projection.sequence[:-2]
    )
    assert _project_accepted_route(realized).retained_non_payload_nt == 21
    assert len(realized.basal_authority.projection.pairing_state.pairs) == 6
    assert type(realized).model_validate_json(realized.model_dump_json()) == realized


def test_asymmetric_release_preserves_association_and_parent_core(tmp_path):
    request, foldback, basal, design, _, encoding = _clone_request(tmp_path)
    baseline = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    data = request.model_dump(mode="python", by_alias=True)
    primer = data["materialization"]["endpoint_auxiliaries"]["forward_primer"]["primer"]["oligo"]
    primer["sequence_5prime"] = "GGTCTCAAAAAA" + encoding[:4]
    del primer["material_id"]
    data["release"]["left"]["payload_end_offset_bp"] = 6
    modified = type(request).model_validate(data)
    result = _discover_raw(modified, foldback=foldback, basal=basal, design=design)
    assert result.realizations, result.failure_reasons
    assert len(result.realizations) == len(baseline.realizations)
    for realized in result.realizations:
        product = realized.final_product
        evidence = product.release_evidence
        assert _project_accepted_route(realized).retained_non_payload_nt == 25
        assert product.encoding_projection is None
        assert evidence is not None
        assert evidence.design_parent_projection.sequence == encoding
        assert evidence.design_parent_projection.source_span.start.offset == 12
        assert evidence.released_union_projection.sequence == "AAAAAA" + encoding
        assert evidence.released_union_projection.source_span.start.offset == 6
        assert evidence.released_union_projection.source_span.end.offset == 39
        assert tuple(end.sequence for end in product.cohesive_ends) == ("AAAA", "AAAA")
        assert realized.basal_authority == baseline.realizations[0].basal_authority
        assert product.strands[0].sequence == ("AAAAAA" + encoding)[:-4]
        assert product.strands[1].sequence.endswith("TT")
        copying = realized.construction_program.transitions[-2].pcr_authority
        top_retained = {
            index
            for span in copying.endpoint_sequence_fate_spans
            if span.endpoint_strand.value == "top" and span.fate.value == "retained_construction"
            for index in range(span.endpoint_span.start.offset, span.endpoint_span.end.offset)
        }
        assert set(range(6, 12)) <= top_retained
        assert not set(range(0, 6)) & top_retained
        pcr_payload = {
            side: {
                index
                for span in copying.endpoint_sequence_fate_spans
                if span.endpoint_strand.value == side and span.fate.value == "payload"
                for index in range(span.endpoint_span.start.offset, span.endpoint_span.end.offset)
            }
            for side in ("top", "bottom")
        }
        assert pcr_payload == {
            "top": set(range(16, 20)) | set(range(31, 35)),
            "bottom": set(range(10, 14)) | set(range(25, 29)),
        }
        released_payload = {
            side: {
                index
                for span in product.endpoint_sequence_fate_spans
                if span.endpoint_strand.value == side and span.fate.value == "payload"
                for index in range(span.endpoint_span.start.offset, span.endpoint_span.end.offset)
            }
            for side in ("top", "bottom")
        }
        assert released_payload == {
            "top": set(range(10, 14)) | set(range(25, 29)),
            "bottom": set(range(4, 8)) | set(range(19, 23)),
        }
        # Full model replay must verify source, copying, cuts and projected fates.
        assert type(realized).model_validate_json(realized.model_dump_json()) == realized
