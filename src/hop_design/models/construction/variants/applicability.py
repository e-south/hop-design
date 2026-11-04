"""Route requirements for coordinates, independent of observed search witnesses."""

from .parameter_contract import ParameterDefinition
from .parameters import ParameterSelection, parameter_definition


def inapplicable_reason(definition: ParameterDefinition, product: str) -> str | None:
    release = (
        definition.stage == "released_insert"
        or definition.key == "release_method"
        or definition.key.startswith("basal_release_")
    )
    if release and product != "released_insert":
        return (
            "This coordinate describes a released insert; this hairpin route has no release step."
        )
    association = definition.stage == "source_adapter_association" or definition.key in {
        "adapter_annealing_min_nt",
        "basal_method",
        "basal_strand",
        "basal_nick_offset_nt",
    }
    if association and product == "hairpin":
        return "This coordinate requires the source/adapter association used by an adapter route."
    return None


def validate_product_parameters(selections: tuple[ParameterSelection, ...], product: str) -> None:
    for selection in selections:
        definition = parameter_definition(selection.key)
        reason = inapplicable_reason(definition, product)
        if reason:
            raise ValueError(
                f"Parameter {selection.key!r} is not applicable to {product}: {reason}"
            )
