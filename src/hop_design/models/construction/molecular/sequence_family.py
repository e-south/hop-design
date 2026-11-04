"""Finite exact members derived from one symbolic stem and unchanged preparation policy."""

from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import iupac_bases, normalize_dna_sequence

from ..comparisons.materials import MaterialRole
from ..discovery.request import ScaffoldDiscoveryRequest
from ..family.request import SharedProperty


class SequenceFamilyRequest(HopModel):
    schema_id: Literal["hop.sequence-family/v1"] = Field(alias="schema")
    base_request: ScaffoldDiscoveryRequest
    stem_domain: str
    max_members: int = Field(ge=1, le=64)
    max_total_branches: int = Field(ge=1, le=1024)
    shared_properties: tuple[SharedProperty, ...]
    shared_material_roles: tuple[MaterialRole, ...]

    @field_validator("stem_domain")
    @classmethod
    def normalize_domain(cls, value: str) -> str:
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def bounded_domain(self) -> Self:
        if len(self.stem_domain) != len(self.base_request.product.stem_arm):
            raise ValueError("A sequence family preserves the base stem length.")
        count = family_cardinality(self.stem_domain, self.max_members)
        if count * self.base_request.max_branches > self.max_total_branches:
            raise ValueError("Required members exceed max_total_branches at the inherited quota.")
        for values in (self.shared_properties, self.shared_material_roles):
            if len(set(values)) != len(values):
                raise ValueError("Shared properties and material roles must not repeat.")
        return self


def family_cardinality(domain: str, max_members: int) -> int:
    """Check the finite member bound without materializing sequence combinations."""
    count = 1
    for symbol in domain:
        count *= len(iupac_bases(symbol))
        if count > max_members:
            raise ValueError("Sequence expansion exceeds max_members; narrow the domain.")
    return count
