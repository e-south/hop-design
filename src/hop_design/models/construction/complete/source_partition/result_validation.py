"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/result_validation.py

Validates selected source-partition authority bindings in complete results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult

from ..evaluation.result import SOURCE_PARTITION_REJECTION_CODES
from ..provisioning import resolve_program_enzyme_definitions
from ..result_contract import validate_materialized_request
from .errors import (
    COMPOSITION_REJECTION_BY_BINDING_FAILURE,
    SourcePartitionBindingError,
)
from .replay import bind_source_partition


def validate_source_partition_result_contract(
    *,
    request: Any,
    provenance: Any,
    authority: SourcePartitionDiscoveryResult | None,
    realizations: tuple[Any, ...],
    rejection_candidates: tuple[Any, ...],
    dispositions: tuple[Any, ...],
    foldback_authority: Any,
    basal_authority: Any,
) -> None:
    """Require request, authority, provenance, and route bindings to agree exactly."""
    requested_result_id = request.source_partition_result_id
    requested_realization_id = request.selected_source_partition_realization_id
    provenance_result_id = provenance.source_partition_result_id
    provenance_realization_id = provenance.source_partition_realization_id
    bindings = tuple(item.source_partition_binding for item in realizations)
    enzyme_policies = (
        foldback_authority.neighborhood.request.enzyme_provisioning,
        *(
            ()
            if basal_authority is None
            else (basal_authority.discovery.request.enzyme_provisioning,)
        ),
    )
    if requested_result_id is None:
        if (
            authority is not None
            or provenance_result_id is not None
            or provenance_realization_id is not None
            or any(binding is not None for binding in bindings)
            or rejection_candidates
        ):
            raise ValueError(
                "An unselected source partition cannot appear in result authority, "
                "provenance, or realization bindings."
            )
        return
    if authority is None:
        raise ValueError("A selected source partition requires its embedded authority.")
    verified = SourcePartitionDiscoveryResult.model_validate(authority.model_dump(mode="python"))
    if (
        verified.result_id != requested_result_id
        or provenance_result_id != requested_result_id
        or provenance_realization_id != requested_realization_id
    ):
        raise ValueError("Selected source partition request, authority, and provenance must agree.")
    if requested_realization_id not in {item.realization_id for item in verified.realizations}:
        raise ValueError("Selected source partition realization must belong to its authority.")
    if any(
        binding is None
        or binding.result_id != requested_result_id
        or binding.realization_id != requested_realization_id
        for binding in bindings
    ):
        raise ValueError("Every accepted route requires the selected source partition binding.")
    assert requested_realization_id is not None
    for realization in realizations:
        route_enzyme_definitions = resolve_program_enzyme_definitions(
            program=realization.construction_program.reaction_programs[0],
            policies=enzyme_policies,
        )
        try:
            expected_binding = bind_source_partition(
                payload=request.payload,
                payload_source_map=realization.payload_source_map,
                source_preparation=realization.source_preparation,
                construction_program=realization.construction_program,
                materials=realization.materials,
                material_uses=realization.material_uses,
                route_enzyme_definitions=route_enzyme_definitions,
                partition_result=verified,
                selected_realization_id=requested_realization_id,
            )
        except SourcePartitionBindingError as exc:
            raise ValueError(
                "Accepted route does not replay selected source-partition molecular facts."
            ) from exc
        if realization.source_partition_binding != expected_binding:
            raise ValueError("Source-partition binding must replay exact route molecular facts.")
    rejected_dispositions = tuple(
        item for item in dispositions if item.rejection_reason in SOURCE_PARTITION_REJECTION_CODES
    )
    if len(rejected_dispositions) != len(rejection_candidates):
        raise ValueError(
            "Every source-partition rejection requires one exact materialized candidate."
        )
    candidate_ids = tuple(item.materialized_realization_id for item in rejection_candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Source-partition rejection candidates must be unique.")
    if set(candidate_ids) & {item.materialized_realization_id for item in realizations}:
        raise ValueError("Accepted and source-partition-rejected realizations must be disjoint.")
    for disposition, candidate in zip(
        rejected_dispositions,
        rejection_candidates,
        strict=True,
    ):
        if candidate.source_partition_binding is not None:
            raise ValueError("A source-partition rejection candidate must remain unbound.")
        validate_materialized_request(
            request=request,
            provenance=provenance,
            disposition=disposition,
            realization=candidate,
        )
        route_enzyme_definitions = resolve_program_enzyme_definitions(
            program=candidate.construction_program.reaction_programs[0],
            policies=enzyme_policies,
        )
        try:
            bind_source_partition(
                payload=request.payload,
                payload_source_map=candidate.payload_source_map,
                source_preparation=candidate.source_preparation,
                construction_program=candidate.construction_program,
                materials=candidate.materials,
                material_uses=candidate.material_uses,
                route_enzyme_definitions=route_enzyme_definitions,
                partition_result=verified,
                selected_realization_id=requested_realization_id,
            )
        except SourcePartitionBindingError as exc:
            expected_reason = COMPOSITION_REJECTION_BY_BINDING_FAILURE[exc.code]
            if disposition.rejection_reason is not expected_reason:
                raise ValueError(
                    "The source-partition rejection reason must replay exact molecular facts."
                ) from exc
        else:
            raise ValueError(
                "A source-partition rejection candidate must fail exact molecular replay."
            )


__all__ = ["validate_source_partition_result_contract"]
