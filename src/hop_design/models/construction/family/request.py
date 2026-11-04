"""Named scaffold variations within one unchanged base product contract."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.scaffold import ScaffoldDimension as ScaffoldDimension

type SharedProperty = Literal[
    "stem_sequence",
    "endpoint",
    "release_interfaces",
    "open_side_paired_positions",
    "loop_side_paired_bp",
    "loop_nt",
    "five_prime_unpaired_nt",
    "three_prime_unpaired_nt",
    "terminal_chemistry",
    "non_loop_sequences",
    "non_stem_sequences",
    "regional_contacts",
    "regional_joins",
]


class ScaffoldFamilyMember(HopModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$")
    loop_nt: int | None = Field(default=None, ge=3)
    loop_side_paired_bp: int | None = Field(default=None, ge=3)

    @model_validator(mode="after")
    def require_variation(self) -> ScaffoldFamilyMember:
        if self.loop_nt is None and self.loop_side_paired_bp is None:
            raise ValueError("A family member must specify a supported scaffold dimension.")
        return self


class FamilyBounds(HopModel):
    max_members: int = Field(ge=1, le=64)
    max_total_search_nodes: int = Field(ge=1, le=12_800_000)
    max_total_continuations: int = Field(ge=1, le=64)


class ScaffoldDisplayPreference(HopModel):
    dimension: ScaffoldDimension
    direction: Literal["ascending", "descending"]


class ConstructionFamilyRequest(HopModel):
    schema_id: Literal["hop.construction-family/v1"] = Field(alias="schema")
    base_request: ProductRequest
    members: tuple[ScaffoldFamilyMember, ...] = Field(min_length=1, max_length=64)
    shared_properties: tuple[SharedProperty, ...]
    display_preferences: tuple[ScaffoldDisplayPreference, ...] = ()
    bounds: FamilyBounds

    @model_validator(mode="after")
    def validate_roster_and_bounds(self) -> ConstructionFamilyRequest:
        names = [m.name for m in self.members]
        if len(names) != len(set(names)):
            raise ValueError("Family member names must be unique.")
        if len(self.members) > self.bounds.max_members:
            raise ValueError("Family exceeds max_members.")
        if len(self.members) > self.bounds.max_total_continuations:
            raise ValueError(
                "Family exceeds max_total_continuations (one selected pair per member)."
            )
        jobs = (self.base_request.foldback, self.base_request.basal)
        nodes = sum(j.search.max_search_nodes for j in jobs if j is not None) * len(self.members)
        if nodes > self.bounds.max_total_search_nodes:
            raise ValueError(
                "Family's declared search-node upper bound exceeds max_total_search_nodes."
            )
        if len(set(self.shared_properties)) != len(self.shared_properties):
            raise ValueError("Shared properties must not repeat.")
        dimensions = [p.dimension for p in self.display_preferences]
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("Display preferences must not repeat dimensions.")
        for dimension in ("loop_nt", "loop_side_paired_bp"):
            values = {
                value
                for member in self.members
                if (value := getattr(member, dimension)) is not None
            }
            if dimension in self.shared_properties and len(values) > 1:
                raise ValueError(f"{dimension} cannot be both shared and varied.")
        self.base_request.construction_source()
        return self
