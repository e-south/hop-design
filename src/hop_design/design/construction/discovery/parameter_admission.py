"""Assess complete candidate coordinates after ordinary molecular replay."""

from typing import Any

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.variants.parameters import ParameterSelection
from hop_design.serialization import canonical_json_bytes

from ..comparisons.controls import stage_contexts
from ..projections.interfaces import preparation_interface
from ..variants.choice_space import choice_space
from ..variants.facts import _variants
from ..variants.parameters.facts import parameter_facts
from ..variants.parameters.filter import selection_reasons


def candidate_parameter_reasons(
    route: MaterializedConstructionRealization,
    product: dict[str, Any],
    option: dict[str, Any],
    parameters: list[dict[str, Any]],
    stage: str,
) -> list[dict[str, Any]]:
    regions = {
        name: _variants(name, context, route.final_product)
        for name, context in stage_contexts(route).items()
    }
    facts = {
        **option,
        "loop_sequence": route.foldback_authority.loop_sequence,
        "molecular_identity": {stage: "candidate"},
        "variants": regions,
        **preparation_interface(route, product),
        "parameter_values": parameter_facts(route, product),
    }
    coordinates = choice_space([facts], [option["label"]], stage)["paths"][0]["values"]
    return selection_reasons(
        coordinates,
        tuple(ParameterSelection.model_validate_json(canonical_json_bytes(p)) for p in parameters),
    )
