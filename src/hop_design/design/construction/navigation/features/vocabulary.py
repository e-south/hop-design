"""One vocabulary and operation description for API, CLI and molecular inspection."""

from hop_design.export.construction.presentation.parameter_labels import parameter_labels
from hop_design.models.construction.variants.parameter_contract import ParameterDefinition
from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.serialization import canonical_json_bytes

from ...intents.base import DesignChoices, Source
from ..types import ChoiceSource, Record
from .operations import parameter_operations


def describe_parameters(choices: ChoiceSource, answer: Record) -> list[Record]:
    """Use already admitted query metadata; never load a route or repeat a query."""
    resolution = choices.resolution
    definitions, receipt = parameter_labels(answer["axes"])
    incompatible = {item["key"] for item in receipt["retained"]}
    restrictions = answer["query"]["parameters"]
    result = []
    for axis in definitions:
        definition = ParameterDefinition.model_validate_json(
            canonical_json_bytes(
                {key: axis[key] for key in ParameterDefinition.model_fields if key in axis}
            )
        )
        operations = parameter_operations(
            definition,
            product=resolution["intent"]["product"],
            permissions=resolution["permissions"],
            live=isinstance(choices, DesignChoices),
        )
        if definition.key in incompatible:
            for name, operation in operations.items():
                if name != "inspect":
                    operation.update(
                        available=False,
                        reason="The captured definition differs; use its producer for operations.",
                    )
        result.append(
            {
                **definition.model_dump(mode="json"),
                "operations": operations,
                "constraints": [
                    p
                    for p in restrictions
                    if parameter_definition(p["key"]).canonical_key == definition.canonical_key
                ],
            }
        )
    return result


def parameter_vocabulary(choices: ChoiceSource, query: Source | None) -> list[Record]:
    if "members" in choices.resolution:
        raise ValueError("Choose member(name) before inspecting its molecular parameters.")
    # Validate the query/reference without performing a preserved-surroundings scan.
    if isinstance(choices, DesignChoices):
        normalized = choices._resolved_query(query)
    else:
        from ...editions.refinement import _resolved_query

        submitted, native = _resolved_query(choices, query)
        normalized = submitted.model_copy(update={"parameters": native.parameters})
    answer = choices.query()
    return describe_parameters(
        choices, {**answer, "query": normalized.model_dump(mode="json", by_alias=True)}
    )
