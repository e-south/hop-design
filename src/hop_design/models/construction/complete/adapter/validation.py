"""Validate an independently complete adapter-ligated hairpin and material lineage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hop_design.models.method import BindingOrientation

from ..material.functions import material_function_spans
from ..material_disposition import derive_route_material_dispositions
from ..pcr.validation import validate_adapter_prefix
from ..state import ConstructionStatePhase

if TYPE_CHECKING:
    from ..realization import MaterializedConstructionRealization


def validate_adapter_realization(item: MaterializedConstructionRealization) -> None:
    validate_adapter_prefix(item)
    program = item.construction_program
    terminal = program.states[-1]
    product = item.final_product
    if (
        len(program.states) != 8
        or len(program.transitions) != 7
        or terminal.phase is not ConstructionStatePhase.ADAPTER_LIGATED
        or len(terminal.molecules) != 1
        or product.reference.topology != "single_stranded_hairpin"
        or product.strands != terminal.molecules
        or product.pairings != terminal.pairings
        or product.cohesive_ends
        or product.endpoint_sequence_fate_spans
    ):
        raise ValueError("An adapter hairpin must end at the exact ligated molecular graph.")
    projection = product.design_projection
    if (
        projection.orientation is not BindingOrientation.SAME_5TO3
        or terminal.molecules[0].sequence[
            projection.source_span.start.offset : projection.source_span.end.offset
        ]
        != projection.sequence
    ):
        raise ValueError("The adapter hairpin must contain its exact design encoding.")
    functions = material_function_spans(
        material_uses=item.material_uses, top=terminal.molecules[0], bottom=None
    )
    if product.material_function_spans != functions:
        raise ValueError("Adapter hairpin material spans must replay exact retained lineage.")
    expected = derive_route_material_dispositions(
        materials=item.materials,
        material_uses=item.material_uses,
        program=program,
        material_function_spans=functions,
    )
    if item.route_material_dispositions != expected:
        raise ValueError("Adapter hairpin dispositions must replay exact material removal.")
