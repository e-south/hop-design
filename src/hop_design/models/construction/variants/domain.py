"""A page of permitted coordinates is distinct from a list of complete designs."""

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from .parameters import parameter_definition


class ParameterDomainQuery(HopModel):
    key: str
    length: int | None = Field(default=None, ge=1, le=1024)
    prefix: str = ""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=32, ge=1, le=64)

    @model_validator(mode="after")
    def valid_coordinate(self) -> "ParameterDomainQuery":
        parameter_definition(self.key)
        if set(self.prefix) - set("ACGT"):
            raise ValueError("Sequence prefixes use exact uppercase A/C/G/T bases.")
        if self.length is not None and len(self.prefix) > self.length:
            raise ValueError("A prefix cannot exceed its requested word length.")
        if self.key != "loop_word" and (self.prefix or self.length is not None):
            raise ValueError("Length and prefix navigation apply to the loop sequence domain.")
        return self
