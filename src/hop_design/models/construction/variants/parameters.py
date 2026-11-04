"""One stage-qualified vocabulary for molecular measurements and selection predicates."""

import re

from pydantic import Field, StrictInt, StrictStr, model_validator

from hop_design.models.base import HopModel

from .parameter_catalog import PARAMETERS as PARAMETERS
from .parameter_contract import ParameterDefinition as ParameterDefinition
from .parameter_contract import category

_BY_KEY = {definition.key: definition for definition in PARAMETERS}
_POSITION = re.compile(r"^basal_(source_base|adapter_base|pair_class)_(0|[1-9][0-9]{0,3})$")


def parameter_definition(key: str) -> ParameterDefinition:
    if key in _BY_KEY:
        return _BY_KEY[key]
    if match := _POSITION.fullmatch(key):
        part, index = match.groups()
        return category(
            key,
            f"{part.replace('_', ' ').capitalize()} at +{index}",
            "basal",
            "source_adapter_association",
            "assembly",
            f"Basal {part.replace('_', ' ')} at zero-based position {index} outward from ligation.",
            representation="contact",
        ).model_copy(update={"position_from_ligation": int(index)})
    raise ValueError(f"Unknown molecular parameter: {key}.")


class ParameterSelection(HopModel):
    key: str
    values: tuple[StrictInt | StrictStr, ...] | None = Field(
        default=None, min_length=1, max_length=256
    )
    minimum: StrictInt | None = None
    maximum: StrictInt | None = None

    @model_validator(mode="after")
    def typed_selection(self) -> "ParameterSelection":
        definition = parameter_definition(self.key)
        if self.values is not None:
            if self.minimum is not None or self.maximum is not None:
                raise ValueError("Choose either exact values or one inclusive integer interval.")
            expected = int if definition.kind == "numeric" else str
            if any(type(value) is not expected for value in self.values):
                raise ValueError("Parameter values must agree with the axis type.")
            if len(set(self.values)) != len(self.values):
                raise ValueError("Parameter values must not repeat.")
        elif definition.kind != "numeric" or self.minimum is None or self.maximum is None:
            raise ValueError("A numeric brush requires both inclusive integer boundaries.")
        elif self.minimum > self.maximum:
            raise ValueError("Parameter interval minimum must not exceed maximum.")
        return self

    def accepts(self, value: int | str | None) -> bool:
        if value is None:
            return False
        if self.values is not None:
            return value in self.values
        assert self.minimum is not None and self.maximum is not None
        return type(value) is int and self.minimum <= value <= self.maximum


def validate_selections(selections: tuple[ParameterSelection, ...]) -> None:
    if len({selection.key for selection in selections}) != len(selections):
        raise ValueError("Declare each parameter once; choices within an axis are alternatives.")
