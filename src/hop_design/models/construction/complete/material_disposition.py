"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material_disposition.py

Derives route-wide retention and removal evidence for exact PCR materials.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from itertools import pairwise

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation

from .material import ExactConstructionMaterial, MaterialUse
from .pcr import EndpointStrand, MaterialFunction, MaterialFunctionSpan
from .program import ConstructionProgram


class MaterialRetentionDisposition(StrEnum):
    """Whether one exact input-material span reaches the endpoint."""

    RETAINED = "retained"
    TRANSIENT = "transient"


class EndpointMaterialOccurrence(HopModel):
    """One exact occurrence of an input-material span in the endpoint."""

    endpoint_strand: EndpointStrand
    endpoint_span: Span
    orientation: BindingOrientation


class RouteMaterialDispositionSpan(HopModel):
    """One gap-free input-material span and its exact route disposition."""

    material_use_id: str = Field(pattern=r"^hop:material-use/[0-9a-f]{64}@1$")
    material_id: str = Field(min_length=1)
    function: MaterialFunction
    material_span: Span
    disposition: MaterialRetentionDisposition
    endpoint_occurrences: tuple[EndpointMaterialOccurrence, ...] = ()
    removal_transition_id: str | None = Field(
        default=None,
        pattern=r"^hop:construction-transition/[0-9a-f]{64}@1$",
    )

    @model_validator(mode="after")
    def validate_disposition(self) -> RouteMaterialDispositionSpan:
        if self.disposition is MaterialRetentionDisposition.RETAINED:
            if not self.endpoint_occurrences or self.removal_transition_id is not None:
                raise ValueError("Retained material requires endpoint occurrences and no removal.")
        elif self.endpoint_occurrences or self.removal_transition_id is None:
            raise ValueError(
                "Transient material requires one exact removal and no endpoint occurrence."
            )
        return self


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _occurrence(
    record: MaterialFunctionSpan,
    *,
    start: int,
    end: int,
) -> EndpointMaterialOccurrence:
    material_start = record.material_span.start.offset
    material_end = record.material_span.end.offset
    endpoint_start = record.endpoint_span.start.offset
    if record.orientation is BindingOrientation.SAME_5TO3:
        mapped_start = endpoint_start + start - material_start
        mapped_end = endpoint_start + end - material_start
    else:
        mapped_start = endpoint_start + material_end - end
        mapped_end = endpoint_start + material_end - start
    return EndpointMaterialOccurrence(
        endpoint_strand=record.endpoint_strand,
        endpoint_span=_span(mapped_start, mapped_end),
        orientation=record.orientation,
    )


def _present_indices(program: ConstructionProgram) -> tuple[dict[str, set[int]], ...]:
    states: list[dict[str, set[int]]] = []
    for state in program.states:
        present: dict[str, set[int]] = defaultdict(set)
        for molecule in state.molecules:
            for lineage in molecule.lineage:
                present[lineage.origin_id].add(lineage.origin_index)
        states.append(dict(present))
    return tuple(states)


def _removal_by_index(
    program: ConstructionProgram,
    *,
    material: ExactConstructionMaterial,
    material_use: MaterialUse,
    present: tuple[dict[str, set[int]], ...],
) -> tuple[str | None, ...]:
    removals: list[str | None] = []
    for index in range(len(material.sequence_5prime)):
        transition_id = None
        for position, transition in enumerate(program.transitions):
            if index in present[position].get(material_use.use_id, set()) and index not in present[
                position + 1
            ].get(material_use.use_id, set()):
                if any(
                    index in later.get(material_use.use_id, set())
                    for later in present[position + 1 :]
                ):
                    raise ValueError("Removed material bases cannot reappear later in the route.")
                transition_id = transition.transition_id
                break
        removals.append(transition_id)
    return tuple(removals)


def derive_route_material_dispositions(
    *,
    materials: tuple[ExactConstructionMaterial, ...],
    material_uses: tuple[MaterialUse, ...],
    program: ConstructionProgram,
    material_function_spans: tuple[MaterialFunctionSpan, ...],
) -> tuple[RouteMaterialDispositionSpan, ...]:
    """Derive a gap-free material partition from endpoint lineage and route states."""
    functions = {
        material_use.use_id: function
        for material_use, function in zip(material_uses, MaterialFunction, strict=True)
    }
    mappings: dict[str, list[MaterialFunctionSpan]] = defaultdict(list)
    for record in material_function_spans:
        mappings[record.material_use_id].append(record)
    present = _present_indices(program)
    result: list[RouteMaterialDispositionSpan] = []
    for material, material_use in zip(materials, material_uses, strict=True):
        retained = mappings[material_use.use_id]
        removals = _removal_by_index(
            program,
            material=material,
            material_use=material_use,
            present=present,
        )
        boundaries = {0, len(material.sequence_5prime)}
        for record in retained:
            boundaries.update((record.material_span.start.offset, record.material_span.end.offset))
        for index in range(1, len(removals)):
            if removals[index] != removals[index - 1]:
                boundaries.add(index)
        ordered = sorted(boundaries)
        for start, end in pairwise(ordered):
            covering = tuple(
                record
                for record in retained
                if record.material_span.start.offset <= start
                and record.material_span.end.offset >= end
            )
            occurrences = tuple(_occurrence(record, start=start, end=end) for record in covering)
            if occurrences:
                result.append(
                    RouteMaterialDispositionSpan(
                        material_use_id=material_use.use_id,
                        material_id=material.material_id,
                        function=functions[material_use.use_id],
                        material_span=_span(start, end),
                        disposition=MaterialRetentionDisposition.RETAINED,
                        endpoint_occurrences=occurrences,
                    )
                )
                continue
            removal_ids = set(removals[start:end])
            if len(removal_ids) != 1 or None in removal_ids:
                raise ValueError("Every transient material span requires one replayed removal.")
            result.append(
                RouteMaterialDispositionSpan(
                    material_use_id=material_use.use_id,
                    material_id=material.material_id,
                    function=functions[material_use.use_id],
                    material_span=_span(start, end),
                    disposition=MaterialRetentionDisposition.TRANSIENT,
                    removal_transition_id=removal_ids.pop(),
                )
            )
    return tuple(result)


__all__ = [
    "EndpointMaterialOccurrence",
    "MaterialRetentionDisposition",
    "RouteMaterialDispositionSpan",
    "derive_route_material_dispositions",
]
