"""Exact preparation restrictions over one recorded snapshot, independent of geometry."""

from collections.abc import Iterable
from functools import cached_property
from typing import Annotated

from pydantic import Field, field_validator

from hop_design.models.base import HopModel


class PreparationMembership(HopModel):
    snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    preparations: tuple[Annotated[str, Field(min_length=1)], ...]

    @field_validator("preparations")
    @classmethod
    def distinct_preparations(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("A membership restriction must not repeat a preparation.")
        return tuple(sorted(values))

    @cached_property
    def identities(self) -> frozenset[str]:
        return frozenset(self.preparations)

    def validate_pool(self, snapshot_digest: str, identities: Iterable[str]) -> None:
        if self.snapshot_digest != snapshot_digest:
            raise ValueError("Preparation membership belongs to a different snapshot.")
        if self.identities - set(identities):
            raise ValueError("Unknown preparation in snapshot membership.")


class PreparationQuery(HopModel):
    """Absence means unrestricted; an explicit empty membership matches nothing."""

    membership: PreparationMembership | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    def includes_preparation(self, identity: str) -> bool:
        return self.membership is None or identity in self.membership.identities

    def validate_membership(self, snapshot_digest: str, identities: Iterable[str]) -> None:
        if self.membership is not None:
            self.membership.validate_pool(snapshot_digest, identities)
