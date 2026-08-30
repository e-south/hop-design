"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_projections.py

Tests lossless scientific projections of verified whole-route composition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.projections import (
    project_complete_construction_summary,
    verify_complete_construction_projection,
)
from hop_design.design.construction.verification import (
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.export.construction import (
    render_projection_csv,
    render_projection_json,
    render_projection_svg,
)
from hop_design.models.construction import (
    ConstructionEndpoint,
    RealizationGrouping,
    SearchCompletionStatus,
)
from hop_design.models.construction.complete import CompositionDispositionStatus
from hop_design.models.construction.projections import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionSummaryRow,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import sha256_digest
from tests.contract.test_foldback_construction_discovery import _nickase, _request
from tests.integration.test_complete_construction_clone import _clone_request
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _construction_request,
    _material,
    _verified_design,
)
from tests.integration.test_complete_construction_pcr import _foldback, _payload


def _verified_result(
    tmp_path: Path,
    endpoint: ConstructionEndpoint,
    *,
    incompatible: bool = False,
    truncated: bool = False,
):
    if endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        request, foldback, basal, design, _, _ = _clone_request(tmp_path)
    else:
        payload = _payload()
        foldback = _foldback(payload)
        basal = _basal_result(
            payload,
            endpoint,
            nick_strand=(
                Strand.BOTTOM if endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX else Strand.TOP
            ),
        )
        design = _verified_design(tmp_path)
        encoding = design.plan.hairpin_encoding_insert.sequence
        adapter = None
        forward = None
        reverse = None
        if endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            local_adapter = next(
                item
                for item in basal.realizations[0].materials
                if item.material_id == "ligation-adapter"
            )
            adapter = _material(
                local_adapter.material_id,
                "CCCC" if incompatible else local_adapter.sequence_5prime,
            )
            forward = _material("forward-primer", encoding[:4])
            reverse = _material(
                "reverse-primer",
                reverse_complement_iupac(encoding[-4:]),
            )
        request = _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
            endpoint=endpoint,
            adapter=adapter,
            forward_primer=forward,
            reverse_primer=reverse,
            complement_five_prime_end=(
                EndChemistry.HYDROXYL
                if incompatible and endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
                else EndChemistry.PHOSPHATE
            ),
        )
    if truncated:
        request = request.model_copy(
            update={"enumeration": request.enumeration.model_copy(update={"max_combinations": 1})}
        )
    return discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=verify_basal_neighborhood_result(basal),
        design=design,
    )


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _projection_content(
    projection: CompleteConstructionSummaryProjection,
) -> dict[str, object]:
    return {
        name: getattr(projection, name)
        for name in type(projection).model_fields
        if name != "projection_id"
    }


@pytest.mark.parametrize(
    "endpoint",
    (
        ConstructionEndpoint.SSDNA_HAIRPIN,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    ),
)
def test_complete_summary_preserves_exact_order_groups_and_authorities(
    tmp_path: Path,
    endpoint: ConstructionEndpoint,
) -> None:
    source = _verified_result(tmp_path / endpoint.value, endpoint)

    projection = project_complete_construction_summary(source)

    assert projection.schema_id == "hop.complete-construction-summary/v1"
    assert projection.renderer_version == "complete-construction-projections/1"
    assert projection.source_result_id == source.result.result_id
    assert projection.endpoint is endpoint
    assert projection.status is SearchCompletionStatus.COMPLETE
    assert projection.accounting == source.result.accounting
    assert projection.material_accounting == source.result.material_accounting
    assert projection.provenance == source.result.provenance
    assert projection.claim_boundary == source.result.claim_boundary
    assert projection.failure_reasons == source.result.failure_reasons
    assert projection.truncation_reasons == source.result.truncation_reasons
    assert projection.upstream_truncation_reasons == source.result.upstream_truncation_reasons
    assert projection.geometry_groups == source.result.geometry_groups
    assert projection.final_product_groups == source.result.final_product_groups
    assert tuple(row.ordinal for row in projection.rows) == tuple(
        item.ordinal for item in source.result.combination_dispositions
    )
    assert tuple(row.status for row in projection.rows) == tuple(
        item.status for item in source.result.combination_dispositions
    )
    assert all(row.achieved_geometry_group_key for row in projection.rows)
    assert all(row.final_product_group_key for row in projection.rows)
    assert all(row.endpoint is endpoint for row in projection.rows)
    assert verify_complete_construction_projection(projection, source) == projection

    if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
        assert projection.projection_id == (
            "hop:complete-construction-summary/"
            "9824570ad2b66b4cbaa7f526397135f26e35df12949f85497237c3be946e00f7@1"
        )
        assert sha256_digest(render_projection_json(projection)) == (
            "sha256:c34cdfcab33197dc13dc53bb21bf75671da76d65d428b318bc74aaa1226e0307"
        )

    json_bytes = render_projection_json(projection)
    assert json_bytes == render_projection_json(projection)
    rendered = json.loads(json_bytes)
    assert rendered["rows"][0]["ordinal"] == 0
    csv_rows = _csv_rows(render_projection_csv(projection))
    assert len(csv_rows) == len(source.result.combination_dispositions)
    assert [int(row["ordinal"]) for row in csv_rows] == list(range(len(csv_rows)))
    assert all(row["source_result_id"] == source.result.result_id for row in csv_rows)
    svg = render_projection_svg(projection).decode("utf-8")
    assert f'data-result-id="{source.result.result_id}"' in svg
    assert "Whole-route composition resolved" in svg
    assert "physical construction was not recorded" in svg
    assert "dashboard" not in svg.lower()
    assert "rank" not in svg.lower()


def test_complete_summary_preserves_infeasible_and_truncated_evidence(tmp_path: Path) -> None:
    infeasible = _verified_result(
        tmp_path / "infeasible",
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        incompatible=True,
    )
    truncated = _verified_result(
        tmp_path / "truncated",
        ConstructionEndpoint.SSDNA_HAIRPIN,
        truncated=True,
    )

    infeasible_projection = project_complete_construction_summary(infeasible)
    truncated_projection = project_complete_construction_summary(truncated)

    assert infeasible_projection.status is SearchCompletionStatus.INFEASIBLE
    assert all(
        row.status is CompositionDispositionStatus.REJECTED
        and row.rejection_reason is not None
        and row.materialized_realization_id is None
        and row.achieved_geometry_group_key is None
        and row.final_product_group_key is None
        for row in infeasible_projection.rows
    )
    assert infeasible_projection.failure_reasons == infeasible.result.failure_reasons
    assert truncated_projection.status is SearchCompletionStatus.TRUNCATED
    assert truncated_projection.truncation_reasons == ("max_combinations",)
    assert truncated_projection.accounting.examined_combinations == 1
    assert len(truncated_projection.rows) == 1
    assert "after exhaustive composition" in render_projection_svg(infeasible_projection).decode(
        "utf-8"
    )
    assert "stopped before" in render_projection_svg(truncated_projection).decode("utf-8")


def test_complete_projection_verification_rejects_source_bound_drift(tmp_path: Path) -> None:
    source = _verified_result(tmp_path, ConstructionEndpoint.CLONE_READY_DUPLEX)
    with pytest.raises(TypeError, match="verified source result"):
        project_complete_construction_summary(source.result)  # type: ignore[arg-type]

    projection = project_complete_construction_summary(source)
    changed_provenance = projection.provenance.model_copy(
        update={"hop_version": f"{projection.provenance.hop_version}-forged"}
    )
    content = _projection_content(projection)
    content["provenance"] = changed_provenance
    forged = CompleteConstructionSummaryProjection.create(**content)

    with pytest.raises(ValueError, match="does not replay its verified source result"):
        verify_complete_construction_projection(forged, source)

    changed_row = projection.rows[0].model_copy(
        update={"achieved_geometry_group_key": f"hop:geometry/{'0' * 64}@1"}
    )
    changed_content = _projection_content(projection)
    changed_content["rows"] = (changed_row, *projection.rows[1:])
    with pytest.raises(ValueError, match="grouping keys must replay exact membership"):
        CompleteConstructionSummaryProjection.create(**changed_content)


def test_complete_summary_rows_reject_partial_or_invented_route_evidence(
    tmp_path: Path,
) -> None:
    complete = project_complete_construction_summary(
        _verified_result(tmp_path / "complete", ConstructionEndpoint.SSDNA_HAIRPIN)
    )
    accepted = complete.rows[0]
    accepted_data = accepted.model_dump(mode="python")
    accepted_data["materialized_realization_id"] = None
    with pytest.raises(ValueError, match="exact route and grouping facts"):
        CompleteConstructionSummaryRow.model_validate(accepted_data)

    accepted_data = accepted.model_dump(mode="python")
    accepted_data["material_ids"] = ()
    with pytest.raises(ValueError, match="exact material accounting"):
        CompleteConstructionSummaryRow.model_validate(accepted_data)

    infeasible = project_complete_construction_summary(
        _verified_result(
            tmp_path / "infeasible",
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            incompatible=True,
        )
    )
    rejected = infeasible.rows[0]
    rejected_data = rejected.model_dump(mode="python")
    rejected_data["endpoint"] = ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
    with pytest.raises(ValueError, match="one reason and no accepted-route facts"):
        CompleteConstructionSummaryRow.model_validate(rejected_data)

    rejected_data = rejected.model_dump(mode="python")
    rejected_data["material_ids"] = ("invented-material",)
    with pytest.raises(ValueError, match="cannot report materialized route evidence"):
        CompleteConstructionSummaryRow.model_validate(rejected_data)


def test_complete_summary_rejects_accounting_order_and_group_drift(tmp_path: Path) -> None:
    projection = project_complete_construction_summary(
        _verified_result(tmp_path, ConstructionEndpoint.CLONE_READY_DUPLEX)
    )

    content = _projection_content(projection)
    changed_row = projection.rows[0].model_copy(update={"ordinal": 1})
    content["rows"] = (changed_row, *projection.rows[1:])
    with pytest.raises(ValueError, match="preserve exact disposition order"):
        CompleteConstructionSummaryProjection.create(**content)

    content = _projection_content(projection)
    content["accounting"] = projection.accounting.model_copy(
        update={"candidate_enzyme_programs": projection.accounting.candidate_enzyme_programs + 1}
    )
    with pytest.raises(ValueError, match="route-attempt accounting"):
        CompleteConstructionSummaryProjection.create(**content)

    content = _projection_content(projection)
    changed_group = projection.geometry_groups[0].model_copy(
        update={"grouping": RealizationGrouping.FINAL_PRODUCT}
    )
    content["geometry_groups"] = (changed_group, *projection.geometry_groups[1:])
    with pytest.raises(ValueError, match="Group key must match the declared grouping dimension"):
        CompleteConstructionSummaryProjection.create(**content)

    substrate_projection = project_complete_construction_summary(
        _verified_result(tmp_path / "duplicate-groups", ConstructionEndpoint.SSDNA_HAIRPIN)
    )
    group = substrate_projection.geometry_groups[0]
    assert len(group.realization_ids) >= 2
    first = group.model_copy(
        update={"realization_ids": group.realization_ids[:1], "multiplicity": 1}
    )
    second = group.model_copy(
        update={
            "realization_ids": group.realization_ids[1:],
            "multiplicity": len(group.realization_ids[1:]),
        }
    )
    content = _projection_content(substrate_projection)
    content["geometry_groups"] = (first, second)
    with pytest.raises(ValueError, match="unique canonical group keys"):
        CompleteConstructionSummaryProjection.create(**content)


def test_complete_summary_rejects_status_and_identity_drift(tmp_path: Path) -> None:
    projection = project_complete_construction_summary(
        _verified_result(tmp_path, ConstructionEndpoint.SSDNA_HAIRPIN)
    )

    content = _projection_content(projection)
    content["status"] = SearchCompletionStatus.TRUNCATED
    with pytest.raises(ValueError, match="require an exact truncation reason"):
        CompleteConstructionSummaryProjection.create(**content)

    content = projection.model_dump(mode="python", by_alias=True)
    content["projection_id"] = f"hop:complete-construction-summary/{'0' * 64}@1"
    with pytest.raises(ValueError, match="must seal the complete summary relation"):
        CompleteConstructionSummaryProjection.model_validate(content)

    truncated = project_complete_construction_summary(
        _verified_result(
            tmp_path / "truncated-complete-forgery",
            ConstructionEndpoint.SSDNA_HAIRPIN,
            truncated=True,
        )
    )
    content = _projection_content(truncated)
    content["status"] = SearchCompletionStatus.COMPLETE
    content["truncation_reasons"] = ()
    content["upstream_truncation_reasons"] = ()
    with pytest.raises(ValueError, match="require exhaustive accounting"):
        CompleteConstructionSummaryProjection.create(**content)

    partial_zero = project_complete_construction_summary(
        _verified_result(
            tmp_path / "truncated-infeasible-forgery",
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            incompatible=True,
            truncated=True,
        )
    )
    assert not tuple(
        row for row in partial_zero.rows if row.status is CompositionDispositionStatus.ACCEPTED
    )
    content = _projection_content(partial_zero)
    content["status"] = SearchCompletionStatus.INFEASIBLE
    content["truncation_reasons"] = ()
    content["upstream_truncation_reasons"] = ()
    with pytest.raises(ValueError, match="require exhaustive accounting"):
        CompleteConstructionSummaryProjection.create(**content)


def test_complete_summary_csv_preserves_zero_combination_context(tmp_path: Path) -> None:
    payload = _payload()
    foldback = discover_foldback_neighborhood(_request(_nickase(motif="GACA", cut_offset=4)))
    basal = _basal_result(payload)
    design = _verified_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
    )
    source = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=verify_basal_neighborhood_result(basal),
        design=design,
    )
    projection = project_complete_construction_summary(source)

    assert projection.status is SearchCompletionStatus.INFEASIBLE
    assert projection.rows == ()
    rows = _csv_rows(render_projection_csv(projection))
    assert len(rows) == 1
    assert rows[0]["status"] == "infeasible"
    assert rows[0]["source_result_id"] == source.result.result_id
    assert rows[0]["examined_combinations"] == "0"
    assert rows[0]["physical_construction"] == "not_recorded"
