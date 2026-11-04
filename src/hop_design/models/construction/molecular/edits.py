"""Stage-bound edits of a captured product intention, never of derived molecules."""

from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import normalize_dna_sequence
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..discovery.placement import EndPlacement
from ..discovery.request import ScaffoldDiscoveryRequest
from ..product_request import ProductEnds


class LoopSequenceEdit(HopModel):
    region: Literal["loop"] = "loop"
    stage: Literal["hairpin"] = "hairpin"
    sequences: tuple[str, ...] = Field(min_length=1, max_length=64)

    @field_validator("sequences")
    @classmethod
    def exact_distinct_words(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        words = tuple(normalize_dna_sequence(w, allow_degenerate=False) for w in value)
        if len(set(words)) != len(words):
            raise ValueError("Loop edit words must be distinct.")
        return words


class ReleasedEndEdit(HopModel):
    region: Literal["released_ends"] = "released_ends"
    stage: Literal["released_insert"] = "released_insert"
    placements: tuple[EndPlacement, ...] = Field(min_length=1, max_length=64)
    ends: ProductEnds | None = None
    basal_nick_enzyme_ids: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=16)
    release_enzyme_ids: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=16)


MolecularEdit = Annotated[LoopSequenceEdit | ReleasedEndEdit, Field(discriminator="region")]


class MolecularEditRequest(HopModel):
    schema_id: Literal["hop.molecular-edit/v1"] = Field(alias="schema")
    original_request: ScaffoldDiscoveryRequest
    original_request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    edits: tuple[MolecularEdit, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def bound_original(self) -> Self:
        if len({edit.region for edit in self.edits}) != len(self.edits):
            raise ValueError("Edit each molecular region only once.")
        digest = sha256_digest(canonical_json_bytes(self.original_request))
        if digest != self.original_request_digest:
            raise ValueError("Molecular edit original request digest does not match.")
        return self
