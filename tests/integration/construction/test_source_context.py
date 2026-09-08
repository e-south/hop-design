"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/construction/test_source_context.py

Checks local junction preservation within a longer exact source context.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest

import hop_design.construction as construction
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.construction import SearchCompletionStatus, SourceOrientation
from hop_design.models.sequence import reverse_complement_iupac
from tests.integration.test_adapter_annealing_completion import _adapter_case
from tests.integration.test_complete_construction_discovery import _discover_raw
from tests.integration.test_construction_source_compiler import (
    _local_receipt,
    _source,
    _write_source,
)


def _context_case(tmp_path: Path, *, reverse: bool = False):
    request, foldback, basal, design = _adapter_case(tmp_path, "AAAA")
    if reverse:
        local_data = foldback.neighborhood.request.model_dump(mode="json", by_alias=True)
        local_data["enzyme_provisioning"]["catalog"]["enzymes"][0][
            "recognition_orientation_semantics"
        ] = "both_orientations"
        foldback = discover_foldback_neighborhood(
            type(foldback.neighborhood.request).model_validate_json(json.dumps(local_data))
        )
    selected = next(
        item
        for item in foldback.realizations
        if item.payload_source_map.segments[0].orientation
        is (SourceOrientation.REVERSE_COMPLEMENT if reverse else SourceOrientation.FORWARD)
    )
    data = request.model_dump(mode="json", by_alias=True)
    data["foldback_result_id"] = foldback.result_id
    data["selected_foldback_realization_id"] = selected.foldback_realization_id
    data["selected_basal_realization_id"] = basal.realizations[0].basal_realization_id
    source = "TGCAGTCTGACAAAAGACATCAGATGCTGA"
    preparation = data["materialization"]["source_preparation"]
    preparation["source_ssdna"] = {
        "mode": "fixed",
        "material": {
            "sequence_5prime": reverse_complement_iupac(source) if reverse else source,
            "five_prime_end": "hydroxyl",
            "three_prime_end": "hydroxyl",
        },
    }
    preparation["reverse_primer" if reverse else "forward_primer"] = {
        "mode": "derive",
        "annealing_length_nt": 15,
    }
    data["materialization"]["endpoint_auxiliaries"]["forward_primer"] = {
        "mode": "derive",
        "annealing_length_nt": 15,
    }
    request = type(request).model_validate_json(json.dumps(data))
    return request, foldback, basal, design


@pytest.mark.parametrize("reverse", (False, True))
def test_fixed_source_supplies_distal_annealing_without_changing_local_junctions(
    tmp_path: Path, reverse: bool
) -> None:
    request, foldback, basal, design = _context_case(tmp_path, reverse=reverse)

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert len(result.realizations) == 1
    item = result.realizations[0]
    assert item.basal_authority == basal.realizations[0]
    assert item.foldback_authority in foldback.realizations
    source = "TGCAGTCTGACAAAAGACATCAGATGCTGA"
    assert item.source_preparation.source_ssdna.sequence_5prime == (
        reverse_complement_iupac(source) if reverse else source
    )
    segment = item.payload_source_map.segments[0]
    assert (segment.source_span.start.offset, segment.source_span.end.offset) == (
        (11, 15) if reverse else (15, 19)
    )
    source_primer = (
        item.source_preparation.reverse_primer
        if reverse
        else item.source_preparation.forward_primer
    )
    assert source_primer.annealing_sequence == "TGCAGTCTGACAAAA"
    assert item.materials[2].sequence_5prime == "TTTTGTCAGACTGCAGATCTG"
    association = item.construction_program.transitions[-3].pcr_authority
    assert len(association.pairings) == 15
    assert (association.hairpin_span.start.offset, association.hairpin_span.end.offset) == (0, 15)
    basal_operation = item.construction_program.reaction_programs[0].stages[0].operations[0]
    cut = (
        basal_operation.intended_binding.reference_cut
        if reverse
        else basal_operation.intended_binding.complement_cut
    )
    assert cut.offset == 15
    assert item.final_product.encoding_projection.sequence == request.design.encoding_sequence


@pytest.mark.parametrize(
    ("sequence", "reason"),
    (
        ("TGCAGTCTGACAAACGACATCAGATGCTGA", "source-preparation-incompatible"),
        ("TGCAGTCTGACAAAAGACTTCAGATGCTGA", "source-preparation-incompatible"),
        ("TGCAGTCTGACAAAAGACATCAGATGCTGT", "source-preparation-incompatible"),
        ("TGCAGTCTGCAAAAGACATCAGATGCTGA", "source-preparation-incompatible"),
        ("AAAAGTCTGACAAAAGACATCAGATGCTGA", "global-actionable-site-conflict"),
    ),
)
def test_fixed_context_cannot_change_junctions_or_hide_additional_cleavage(
    tmp_path: Path, sequence: str, reason: str
) -> None:
    request, foldback, basal, design = _context_case(tmp_path)
    data = request.model_dump(mode="json", by_alias=True)
    data["materialization"]["source_preparation"]["source_ssdna"]["material"]["sequence_5prime"] = (
        sequence
    )
    del data["materialization"]["source_preparation"]["source_ssdna"]["material"]["material_id"]
    request = type(request).model_validate_json(json.dumps(data))

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert not result.realizations
    assert {item.code for item in result.failure_reasons} == {reason}


def test_fixed_context_does_not_rewrite_a_pinned_endpoint_primer(tmp_path: Path) -> None:
    request, foldback, basal, design = _context_case(tmp_path)
    data = request.model_dump(mode="json", by_alias=True)
    data["materialization"]["endpoint_auxiliaries"]["forward_primer"] = {
        "mode": "fixed",
        "primer": {
            "annealing_length_nt": 15,
            "oligo": {
                "sequence_5prime": "AGCAGTCTGACAAAA",
                "five_prime_end": "hydroxyl",
                "three_prime_end": "hydroxyl",
            },
        },
    }
    request = type(request).model_validate_json(json.dumps(data))

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert {item.code for item in result.failure_reasons} == {"pcr-primer-mismatch"}


def test_extended_source_survives_public_compilation_and_portable_replay(tmp_path: Path) -> None:
    request, foldback, basal, _ = _context_case(tmp_path)
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=request.endpoint,
        materialization=request.materialization,
    )
    compiled = construction.compile_construction_from_local_realizations(
        _write_source(tmp_path / "source.yaml", source),
        design_bundle_path=tmp_path / "design",
        foldback=_local_receipt(tmp_path / "foldback.json", foldback),
        foldback_realization_id=request.selected_foldback_realization_id,
        basal=_local_receipt(tmp_path / "basal.json", basal),
        basal_realization_id=request.selected_basal_realization_id,
    )

    assert compiled.status == "complete"
    assert compiled.nominal_combinations == compiled.valid_realizations == 1
    replayed = construction.load_verified_construction_bundle(compiled.write(tmp_path / "bundle"))
    assert replayed.bundle_id == compiled.bundle_id
    assert replayed.valid_realizations == 1


def _searched_context_case(tmp_path: Path, *, pattern: str = "MAAAGTCTGAC", reverse: bool = False):
    request, foldback, basal, design = _context_case(tmp_path, reverse=reverse)
    data = request.model_dump(mode="json", by_alias=True)
    data["materialization"]["source_preparation"]["source_ssdna"] = {
        "mode": "constrain",
        "upstream_sequence_spec": pattern,
        "five_prime_end": "hydroxyl",
        "three_prime_end": "hydroxyl",
    }
    request = type(request).model_validate_json(json.dumps(data))
    return request, foldback, basal, design


@pytest.mark.parametrize("reverse", (False, True))
def test_source_context_search_preserves_rejection_and_finds_later_completion(
    tmp_path: Path, reverse: bool
) -> None:
    request, foldback, basal, design = _searched_context_case(tmp_path, reverse=reverse)

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.accounting.nominal_combinations == result.accounting.examined_combinations == 2
    assert result.accounting.rejected_combinations == result.accounting.valid_realizations == 1
    assert [item.source_context_sequence for item in result.combination_dispositions] == [
        "AAAAGTCTGAC",
        "CAAAGTCTGAC",
    ]
    assert result.combination_dispositions[0].rejection_reason == "global-actionable-site-conflict"
    item = result.realizations[0]
    sequence = "CAAAGTCTGACAAAAGACATCAGATGCTGA"
    assert item.source_preparation.source_ssdna.sequence_5prime == (
        reverse_complement_iupac(sequence) if reverse else sequence
    )
    assert item.source_preparation.source_ssdna_use.specification_resolution_mode == "constrain"
    assert item.basal_authority == basal.realizations[0]
    assert len(item.construction_program.transitions[-3].pcr_authority.pairings) == 15


def test_source_context_search_does_not_call_a_stopped_prefix_infeasible(tmp_path: Path) -> None:
    request, foldback, basal, design = _searched_context_case(tmp_path)
    data = request.model_dump(mode="json", by_alias=True)
    data["enumeration"]["max_combinations"] = 1
    request = type(request).model_validate_json(json.dumps(data))

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.accounting.nominal_combinations == 2
    assert result.accounting.examined_combinations == result.accounting.rejected_combinations == 1
    assert result.truncation_reasons == ("max_combinations",)
    assert not result.realizations


def test_source_context_search_preserves_alternatives_and_reports_hit_limit(tmp_path: Path) -> None:
    request, foldback, basal, design = _searched_context_case(tmp_path, pattern="SAAAGTCTGAC")
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.accounting.valid_realizations == 2
    assert len({item.materialized_realization_id for item in result.realizations}) == 2
    assert len(result.geometry_groups) == 1
    assert len(result.geometry_groups[0].realization_ids) == 2

    data = request.model_dump(mode="json", by_alias=True)
    data["enumeration"]["max_realizations"] = 1
    limited = _discover_raw(
        type(request).model_validate_json(json.dumps(data)),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert limited.status is SearchCompletionStatus.TRUNCATED
    assert limited.truncation_reasons == ("max_realizations",)
    assert (
        limited.realizations[0].materialized_realization_id
        == result.realizations[0].materialized_realization_id
    )


@pytest.mark.parametrize(
    ("pattern", "reason"),
    (
        ("AAAAGTCTGAC", "global-actionable-site-conflict"),
        ("TGCAGTCTGC", "source-preparation-incompatible"),
    ),
)
def test_exhausted_source_context_domain_retains_its_molecular_failure(
    tmp_path: Path, pattern: str, reason: str
) -> None:
    request, foldback, basal, design = _searched_context_case(tmp_path, pattern=pattern)
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert result.accounting.nominal_combinations == result.accounting.rejected_combinations == 1
    assert result.combination_dispositions[0].rejection_reason == reason


def test_source_context_search_survives_public_bundle_and_tidy_projection(tmp_path: Path) -> None:
    request, foldback, basal, _ = _searched_context_case(tmp_path)
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=request.endpoint,
        materialization=request.materialization,
    )
    compiled = construction.compile_construction_from_local_realizations(
        _write_source(tmp_path / "source.yaml", source),
        design_bundle_path=tmp_path / "design",
        foldback=_local_receipt(tmp_path / "foldback.json", foldback),
        foldback_realization_id=request.selected_foldback_realization_id,
        basal=_local_receipt(tmp_path / "basal.json", basal),
        basal_realization_id=request.selected_basal_realization_id,
    )
    assert compiled.nominal_combinations == 2
    assert compiled.valid_realizations == 1
    replayed = construction.load_verified_construction_bundle(compiled.write(tmp_path / "bundle"))
    assert replayed.bundle_id == compiled.bundle_id
    projection = construction.project_complete_construction_summary(replayed)
    assert projection.csv_bytes is not None
    assert b"source_context_sequence" in projection.csv_bytes
    assert b"AAAAGTCTGAC" in projection.csv_bytes
    assert b"CAAAGTCTGAC" in projection.csv_bytes


@pytest.mark.parametrize("sequence", (None, "AAAAGTCTGAC", "TAAAGTCTGAC"))
def test_resealed_completion_cannot_change_the_examined_assignment(
    tmp_path: Path, sequence: str | None
) -> None:
    request, foldback, basal, design = _searched_context_case(tmp_path)
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    dispositions = list(result.combination_dispositions)
    dispositions[1] = dispositions[1].model_copy(update={"source_context_sequence": sequence})
    draft = result.model_copy(update={"combination_dispositions": tuple(dispositions)})
    data = draft.model_dump(mode="python")
    data["result_id"] = draft._expected_result_id()
    with pytest.raises(ValueError, match="ordered upstream domains"):
        type(result).model_validate(data)


def test_upstream_completion_requires_a_basal_neighborhood(tmp_path: Path) -> None:
    request, _, _, _ = _searched_context_case(tmp_path)
    data = request.model_dump(mode="json", by_alias=True)
    data["endpoint"] = "ssdna_hairpin"
    data["basal_result_id"] = None
    data.pop("selected_basal_realization_id")
    data["materialization"]["endpoint_auxiliaries"] = None
    with pytest.raises(ValueError, match="Upstream context search requires a basal"):
        type(request).model_validate_json(json.dumps(data))


def test_all_completions_constraint_preserves_each_sequence_disposition(tmp_path: Path) -> None:
    request, foldback, basal, design = _searched_context_case(tmp_path)
    data = request.model_dump(mode="json", by_alias=True)
    data["whole_route_constraints"]["require_all_combinations_valid"] = True
    request = type(request).model_validate_json(json.dumps(data))
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert [item.source_context_sequence for item in result.combination_dispositions] == [
        "AAAAGTCTGAC",
        "CAAAGTCTGAC",
    ]
    assert {item.code for item in result.failure_reasons} == {
        "global-actionable-site-conflict",
        "all-combinations-valid-required",
    }
