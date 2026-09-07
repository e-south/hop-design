"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_trajectory.py

Tests exact trajectory projections of caller-selected construction realizations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest
from pydantic import ValidationError

from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.discovery import VerifiedConstructionSpaceResult
from hop_design.design.construction.projections import (
    project_complete_construction_trajectory,
    verify_complete_construction_trajectory,
)
from hop_design.design.construction.verification import (
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.export.construction import render_projection_json, render_projection_svg
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete import ConstructionDiscoveryRequest
from hop_design.models.construction.projections import (
    CompleteConstructionTrajectoryProjection,
)
from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_complete_construction_bundle import _verified_construction
from tests.integration.test_complete_construction_clone import _clone_request
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _construction_request,
    _material,
    _verified_design,
)
from tests.integration.test_complete_construction_pcr import _foldback, _payload
from tests.integration.test_complete_construction_source_partition import _case


def _verified_pcr_source(tmp_path: Path) -> VerifiedConstructionSpaceResult:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter_sequence = basal.realizations[0].proximal_adapter_sequence
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        adapter=_material("ligation-adapter", adapter_sequence),
        forward_primer=_material("forward-primer", encoding[:4]),
        reverse_primer=_material("reverse-primer", reverse_complement_iupac(encoding[-4:])),
    )
    return discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=verify_basal_neighborhood_result(basal),
        design=design,
    )


def _verified_clone_source(tmp_path: Path) -> VerifiedConstructionSpaceResult:
    request, foldback, basal, design, _, _ = _clone_request(tmp_path)
    return discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=verify_basal_neighborhood_result(basal),
        design=design,
    )


def _source_with_rejection(tmp_path: Path) -> VerifiedConstructionSpaceResult:
    source = _verified_construction(tmp_path)
    request_data = source.result.request.model_dump(mode="python")
    request_data["materialization"]["source_preparation"]["source_ssdna"] = {
        "mode": "fixed",
        "material": source.result.realizations[0].source_preparation.source_ssdna.model_dump(
            mode="python"
        ),
    }
    request = ConstructionDiscoveryRequest.model_validate(request_data)
    return discover_constructions(
        request,
        foldback=source.foldback,
        basal=source.basal,
        design=source.design,
    )


def _assert_visible_associations(svg: str, source: VerifiedConstructionSpaceResult) -> None:
    root = ElementTree.fromstring(svg)
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    selected = source.result.realizations[0]
    expected_strands = {
        (state.state_id, strand.strand_id): strand.sequence
        for state in selected.construction_program.states
        for strand in state.molecules
    }
    visible_strand_chunks: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for state_node in root.findall(".//svg:g[@data-state-id]", namespace):
        state_id = state_node.attrib["data-state-id"]
        for row in state_node.findall(".//svg:text[@data-visible-strand-id]", namespace):
            sequence_chunk = row.attrib["data-sequence-chunk"]
            assert sequence_chunk in "".join(row.itertext())
            visible_strand_chunks.setdefault(
                (state_id, row.attrib["data-visible-strand-id"]),
                [],
            ).append((int(row.attrib["data-sequence-chunk-index"]), sequence_chunk))
    visible_strands = {
        key: "".join(chunk for _, chunk in sorted(chunks))
        for key, chunks in visible_strand_chunks.items()
    }
    assert visible_strands == expected_strands

    expected_pairs = {
        (
            state.state_id,
            pair.left_strand_id,
            pair.left_index,
            pair.left_base,
            pair.right_strand_id,
            pair.right_index,
            pair.right_base,
            pair.kind.value,
        )
        for state in selected.construction_program.states
        for pair in state.pairings
    }
    visible_pairs: set[tuple[str, str, int, str, str, int, str, str]] = set()
    for state_node in root.findall(".//svg:g[@data-state-id]", namespace):
        state_id = state_node.attrib["data-state-id"]
        for row in state_node.findall(
            ".//svg:text[@data-visible-association='pairing']",
            namespace,
        ):
            left_relations = row.attrib["data-left-relations"].split(",")
            right_relations = row.attrib["data-right-relations"].split(",")
            assert len(left_relations) == len(right_relations)
            visible_text = "".join(row.itertext())
            assert row.attrib["data-left-relations"] in visible_text
            assert row.attrib["data-right-relations"] in visible_text
            for left_relation, right_relation in zip(
                left_relations,
                right_relations,
                strict=True,
            ):
                left_index, left_base = left_relation.split(":")
                right_index, right_base = right_relation.split(":")
                visible_pairs.add(
                    (
                        state_id,
                        row.attrib["data-left-strand-id"],
                        int(left_index),
                        left_base,
                        row.attrib["data-right-strand-id"],
                        int(right_index),
                        right_base,
                        row.attrib["data-pair-kind"],
                    )
                )
    assert visible_pairs == expected_pairs

    expected_bonds = {
        (
            state.state_id,
            item.bond.upstream_strand_id,
            item.bond.downstream_strand_id,
            item.product_strand_id,
        )
        for state in selected.construction_program.states
        for item in state.formed_bonds
    }
    visible_bonds = {
        (
            state_node.attrib["data-state-id"],
            row.attrib["data-upstream-strand-id"],
            row.attrib["data-downstream-strand-id"],
            row.attrib["data-product-strand-id"],
        )
        for state_node in root.findall(".//svg:g[@data-state-id]", namespace)
        for row in state_node.findall(
            ".//svg:text[@data-visible-association='bond']",
            namespace,
        )
    }
    assert visible_bonds == expected_bonds

    content_right = 1128
    approximate_monospace_width = 8
    bounded_rows = root.findall(".//svg:text[@data-layout-row='bounded']", namespace)
    assert bounded_rows
    for row in bounded_rows:
        visible_text = "".join(row.itertext())
        assert (
            int(row.attrib["x"]) + len(visible_text) * approximate_monospace_width <= content_right
        )


def test_complete_trajectory_embeds_one_selected_route_verbatim(
    tmp_path: Path,
) -> None:
    source = _verified_construction(tmp_path)
    selected = source.result.realizations[0]
    disposition = next(
        item
        for item in source.result.combination_dispositions
        if item.materialized_realization_id == selected.materialized_realization_id
    )

    projection = project_complete_construction_trajectory(
        source,
        materialized_realization_id=selected.materialized_realization_id,
    )

    assert projection.schema_id == "hop.complete-construction-trajectory/v4"
    assert projection.renderer_version == "complete-construction-trajectory/3"
    assert projection.source_result_id == source.result.result_id
    assert projection.composition_ordinal == disposition.ordinal
    assert projection.realization == selected
    assert projection.projection_id.startswith("hop:complete-construction-trajectory/")
    assert verify_complete_construction_trajectory(projection, source) == projection
    assert render_projection_json(projection) == canonical_json_bytes(projection)

    svg = render_projection_svg(projection).decode()
    assert render_projection_svg(projection).decode() == svg
    ElementTree.fromstring(svg)
    assert f'data-projection-id="{projection.projection_id}"' in svg
    assert f'data-projection-schema="{projection.schema_id}"' in svg
    assert f'data-renderer-version="{projection.renderer_version}"' in svg
    assert f'data-result-id="{source.result.result_id}"' in svg
    assert f'data-realization-id="{selected.materialized_realization_id}"' in svg
    assert 'data-composition-ordinal="0"' in svg
    assert "selected composition ordinal 0" in svg
    for state in selected.construction_program.states:
        assert f'data-state-id="{state.state_id}"' in svg
        assert state.phase.value.replace("_", " ") in svg
        for strand in state.molecules:
            assert f'data-strand-id="{strand.strand_id}"' in svg
            assert f'data-sequence="{strand.sequence}"' in svg
            assert f'data-five-prime-end="{strand.five_prime_end.value}"' in svg
            assert f'data-three-prime-end="{strand.three_prime_end.value}"' in svg
        for pair in state.pairings:
            assert f'data-pair-left-strand="{pair.left_strand_id}"' in svg
            assert f'data-pair-left-index="{pair.left_index}"' in svg
            assert f'data-pair-left-base="{pair.left_base}"' in svg
            assert f'data-pair-right-strand="{pair.right_strand_id}"' in svg
            assert f'data-pair-right-index="{pair.right_index}"' in svg
            assert f'data-pair-right-base="{pair.right_base}"' in svg
            assert f'data-pair-kind="{pair.kind.value}"' in svg
        for bond in state.formed_bonds:
            assert f'data-bond-upstream-strand="{bond.bond.upstream_strand_id}"' in svg
            assert f'data-bond-upstream-end="{bond.bond.upstream_end.value}"' in svg
            assert f'data-bond-downstream-strand="{bond.bond.downstream_strand_id}"' in svg
            assert f'data-bond-downstream-end="{bond.bond.downstream_end.value}"' in svg
            assert f'data-bond-product-strand="{bond.product_strand_id}"' in svg
    for transition in selected.construction_program.transitions:
        assert f'data-transition-id="{transition.transition_id}"' in svg
    _assert_visible_associations(svg, source)
    for program in selected.construction_program.reaction_programs:
        for stage in program.stages:
            for operation in stage.operations:
                binding = operation.intended_binding
                reference_cut = (
                    "none" if binding.reference_cut is None else str(binding.reference_cut.offset)
                )
                complement_cut = (
                    "none" if binding.complement_cut is None else str(binding.complement_cut.offset)
                )
                assert f'data-operation-id="{operation.operation_id}"' in svg
                assert f'data-recognition-start="{binding.recognition_span.start.offset}"' in svg
                assert f'data-recognition-end="{binding.recognition_span.end.offset}"' in svg
                assert f'data-reference-cut="{reference_cut}"' in svg
                assert f'data-complement-cut="{complement_cut}"' in svg
    assert "Digital route only" in svg
    assert "No physical construction, QC, or biological activity is established." in svg


def test_complete_trajectory_starts_with_recorded_source_duplex_preparation(
    tmp_path: Path,
) -> None:
    source = _verified_construction(tmp_path)
    selected = source.result.realizations[0]
    preparation = selected.source_preparation
    projection = project_complete_construction_trajectory(
        source,
        materialized_realization_id=selected.materialized_realization_id,
    )

    svg = render_projection_svg(projection).decode()

    assert selected.construction_program.states[0] == preparation.product_state
    assert f'data-source-preparation-id="{preparation.authority_id}"' in svg
    assert f'data-source-preparation-pre-state="{preparation.pre_state_id}"' in svg
    assert f'data-source-preparation-post-state="{preparation.post_state_id}"' in svg
    expected_materials = (
        ("source_ssdna", preparation.source_ssdna),
        ("source_forward_primer", preparation.forward_primer.oligo),
        ("source_reverse_primer", preparation.reverse_primer.oligo),
    )
    for role, material in expected_materials:
        assert f'data-source-preparation-material-role="{role}"' in svg
        assert f'data-material-id="{material.material_id}"' in svg
        assert f'data-material-sequence="{material.sequence_5prime}"' in svg
        assert f'data-material-five-prime-end="{material.five_prime_end.value}"' in svg
        assert f'data-material-three-prime-end="{material.three_prime_end.value}"' in svg
    for binding in preparation.bindings:
        assert f'data-source-preparation-binding-id="{binding.binding_id}"' in svg
        assert f'data-primer-id="{binding.primer_id}"' in svg
        assert f'data-template-strand-id="{binding.template_strand_id}"' in svg
        assert f'data-template-start="{binding.template_span.start.offset}"' in svg
        assert f'data-template-end="{binding.template_span.end.offset}"' in svg
        assert f'data-binding-orientation="{binding.orientation.value}"' in svg
    assert "Template copy produces the exact source duplex." in svg
    preparation_index = svg.index(f'data-source-preparation-id="{preparation.authority_id}"')
    first_program_state_index = svg.index(f'data-state-id="{preparation.product_state.state_id}"')
    assert preparation_index < first_program_state_index


def test_complete_trajectory_embeds_the_selected_source_partition_certificate(
    tmp_path: Path,
) -> None:
    request, foldback, design, partition, _ = _case(tmp_path)
    source = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    )
    selected = source.result.realizations[0]
    binding = selected.source_partition_binding
    assert binding is not None
    certificate = partition.realizations[0].fragment_certificate

    projection = project_complete_construction_trajectory(
        source,
        materialized_realization_id=selected.materialized_realization_id,
    )
    svg = render_projection_svg(projection).decode()

    assert projection.source_partition_certificate == certificate
    assert f'data-source-partition-binding-id="{binding.binding_id}"' in svg
    assert f'data-source-partition-result-id="{binding.result_id}"' in svg
    assert f'data-source-partition-realization-id="{binding.realization_id}"' in svg
    assert (
        'data-selected-maximum-sacrificial-fragment-nt="'
        f'{certificate.selected_maximum_sacrificial_fragment_nt}"' in svg
    )
    for fragment in certificate.fragments:
        assert f'data-partition-fragment-id="{fragment.fragment_id}"' in svg
        assert f'data-source-start="{fragment.source_span.start.offset}"' in svg
        assert f'data-source-end="{fragment.source_span.end.offset}"' in svg
        assert f'data-fragment-disposition="{fragment.disposition.value}"' in svg

    with pytest.raises(ValidationError, match="binding and fragment certificate"):
        CompleteConstructionTrajectoryProjection.model_validate(
            {
                **projection.model_dump(mode="python", by_alias=True),
                "source_partition_certificate": None,
            }
        )


@pytest.mark.parametrize(
    ("source_factory", "terminal_phase"),
    [
        (_verified_pcr_source, "hairpin_pcr_duplex"),
        (_verified_clone_source, "clone_ready_duplex"),
    ],
)
def test_complete_trajectory_renders_recorded_pcr_and_clone_phases(
    tmp_path: Path,
    source_factory,
    terminal_phase: str,
) -> None:
    source = source_factory(tmp_path)
    selected = source.result.realizations[0]

    projection = project_complete_construction_trajectory(
        source,
        materialized_realization_id=selected.materialized_realization_id,
    )
    svg = render_projection_svg(projection).decode()

    assert projection.realization.construction_program.states[-1].phase == terminal_phase
    assert f'data-phase="{terminal_phase}"' in svg
    assert tuple(
        state.state_id for state in projection.realization.construction_program.states
    ) == tuple(state.state_id for state in selected.construction_program.states)
    assert tuple(
        transition.transition_id
        for transition in projection.realization.construction_program.transitions
    ) == tuple(transition.transition_id for transition in selected.construction_program.transitions)
    _assert_visible_associations(svg, source)
    if terminal_phase == "clone_ready_duplex":
        assert selected.final_product.cohesive_ends
        for end in selected.final_product.cohesive_ends:
            assert f'data-cohesive-product-end="{end.product_end}"' in svg
            assert f'data-cohesive-sequence="{end.sequence}"' in svg
            assert f'data-cohesive-protruding-strand="{end.protruding_strand_id}"' in svg
            assert f'data-cohesive-overhang-end="{end.overhang_end.value}"' in svg
            assert f'data-cohesive-primary-cut="{end.primary_cut.offset}"' in svg
            assert f'data-cohesive-complementary-cut="{end.complementary_cut.offset}"' in svg


def test_complete_trajectory_requires_an_explicit_accepted_realization(
    tmp_path: Path,
) -> None:
    source = _source_with_rejection(tmp_path)
    rejected = next(
        item for item in source.result.combination_dispositions if item.status.value == "rejected"
    )

    with pytest.raises(ValueError, match="Rejected construction compositions"):
        project_complete_construction_trajectory(
            source,
            materialized_realization_id=rejected.foldback_realization_id,
        )
    with pytest.raises(ValueError, match="Unknown accepted materialized"):
        project_complete_construction_trajectory(
            source,
            materialized_realization_id=(f"hop:materialized-construction/{'0' * 64}@1"),
        )
    with pytest.raises(TypeError):
        project_complete_construction_trajectory(source)  # type: ignore[call-arg]


def test_complete_trajectory_rejects_unverified_sources_and_forged_admission(
    tmp_path: Path,
) -> None:
    source = _verified_construction(tmp_path)
    selected_id = source.result.realizations[0].materialized_realization_id

    with pytest.raises(TypeError, match="verified source result"):
        project_complete_construction_trajectory(  # type: ignore[arg-type]
            source.result,
            materialized_realization_id=selected_id,
        )

    forged = object.__new__(VerifiedConstructionSpaceResult)
    object.__setattr__(
        forged,
        "result",
        source.result.model_copy(update={"projection_inventory": ()}),
    )
    object.__setattr__(forged, "foldback", source.foldback)
    object.__setattr__(forged, "basal", source.basal)
    object.__setattr__(forged, "design", source.design)
    object.__setattr__(
        forged,
        "_result_digest",
        sha256_digest(canonical_json_bytes(forged.result)),
    )
    with pytest.raises(ValueError, match="deterministic composition replay"):
        project_complete_construction_trajectory(
            forged,
            materialized_realization_id=selected_id,
        )


def test_complete_trajectory_verifier_rejects_source_relation_drift(
    tmp_path: Path,
) -> None:
    source = _verified_construction(tmp_path)
    selected = source.result.realizations[0]
    projection = project_complete_construction_trajectory(
        source,
        materialized_realization_id=selected.materialized_realization_id,
    )
    drifted = CompleteConstructionTrajectoryProjection.create(
        source_result_id=source.result.result_id,
        composition_ordinal=projection.composition_ordinal + 1,
        realization=selected,
    )

    with pytest.raises(ValueError, match="does not replay its verified source"):
        verify_complete_construction_trajectory(drifted, source)

    source_drift = CompleteConstructionTrajectoryProjection.create(
        source_result_id=f"hop:construction-space-result/{'0' * 64}@1",
        composition_ordinal=projection.composition_ordinal,
        realization=selected,
    )
    with pytest.raises(ValueError, match="does not replay its verified source"):
        verify_complete_construction_trajectory(source_drift, source)

    alternate = source.result.realizations[1]
    relation_drift = CompleteConstructionTrajectoryProjection.create(
        source_result_id=source.result.result_id,
        composition_ordinal=projection.composition_ordinal,
        realization=alternate,
    )
    with pytest.raises(ValueError, match="does not replay its verified source"):
        verify_complete_construction_trajectory(relation_drift, source)

    invalid_id = projection.model_dump(mode="python", by_alias=True)
    invalid_id["projection_id"] = f"hop:complete-construction-trajectory/{'0' * 64}@1"
    with pytest.raises(ValueError, match="projection_id must seal"):
        CompleteConstructionTrajectoryProjection.model_validate(invalid_id)
