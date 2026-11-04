"""Strict, resumable frontiers over conditional auxiliary-completion groups."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

Geometry = tuple[int, int, int, int, int, int]


class CompletionWork(HopModel):
    """Next exact word of one local pair; iteration counts attempts, not skipped words."""

    pair: int = Field(default=0, ge=0)
    member: int = Field(default=0, ge=0)
    iteration: int = Field(default=0, ge=0)
    excluded_context_patterns: tuple[
        Annotated[str, Field(pattern=r"^[ACGTRYSWKMBDHVN]+$", max_length=256)], ...
    ] = Field(default=(), max_length=100_000)

    @model_validator(mode="after")
    def exclusion_order(self) -> "CompletionWork":
        if self.excluded_context_patterns != tuple(sorted(set(self.excluded_context_patterns))):
            raise ValueError("Context exclusions must be sorted and unique.")
        if len({len(p) for p in self.excluded_context_patterns}) > 1:
            raise ValueError("Context exclusions must describe one length-bound group.")
        if self.iteration == 0 and (self.member or self.excluded_context_patterns):
            raise ValueError("A pair's first attempt must start at its unconditioned first word.")
        if self.iteration > self.member:
            raise ValueError("An attempt cannot revisit earlier completion words.")
        return self


class CompletionFrontierEntry(HopModel):
    """Next geometry, local page, or group in an admitted page."""

    kind: Literal["geometry", "basal", "foldback", "page", "group", "work"]
    wave: int = Field(ge=0)
    geometry: Geometry
    depth: int = Field(default=0, ge=0)
    page: int = Field(default=-1, ge=-1)
    group: int = Field(default=0, ge=0)
    groups: int = Field(default=1, ge=1)
    work: CompletionWork | None = None

    @model_validator(mode="after")
    def entry_bounds(self) -> "CompletionFrontierEntry":
        if any(n < 0 for n in self.geometry):
            raise ValueError("Frontier geometry must contain nonnegative coordinates.")
        if self.kind in {"geometry", "basal", "foldback"} and (self.depth or self.page != -1):
            raise ValueError("Geometry discovery cannot contain a local page.")
        if self.kind not in {"group", "work"} and (self.group or self.groups != 1):
            raise ValueError("Only a group stream has a conditional group extent.")
        if self.kind == "group" and (self.page < 0 or self.group >= self.groups):
            raise ValueError("A group stream must lie inside its admitted page and extent.")
        if (self.kind == "work") != (self.work is not None):
            raise ValueError("Only a work entry carries a pending molecular attempt.")
        if self.kind == "work" and (self.page < 0 or self.groups != 1):
            raise ValueError("Pending work requires one exact page and group address.")
        return self

    def priority(self) -> tuple[int, int, Geometry, int, int, int, int]:
        return (
            self.wave,
            self.group,
            self.geometry,
            self.page + int(self.kind == "page"),
            ("geometry", "basal", "foldback", "page", "group", "work").index(self.kind),
            -1 if self.work is None else self.work.pair,
            -1 if self.work is None else self.work.iteration,
        )


class PreferredCompletionGroup(HopModel):
    """One admitted group to introduce before the ordinary traversal."""

    geometry: Geometry
    page: int = Field(ge=0)
    group: int = Field(ge=0)
    depth: int = Field(ge=0)

    @model_validator(mode="after")
    def nonnegative_geometry(self) -> "PreferredCompletionGroup":
        if any(n < 0 for n in self.geometry):
            raise ValueError("Preferred geometry requires nonnegative coordinates.")
        return self

    @property
    def address(self) -> tuple[Geometry, int, int]:
        return self.geometry, self.page, self.group


class CompletionSeekCursor(HopModel):
    schema_name: Literal[
        "hop.context-group-seek/v4", "hop.context-group-seek/v7", "hop.context-group-seek/v8"
    ] = Field(default="hop.context-group-seek/v4", alias="schema")
    initialized: bool = False
    frontier: tuple[CompletionFrontierEntry, ...] = Field(default=(), max_length=100_000)
    observed_classes: tuple[Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...] = Field(
        default=(), max_length=100_000, exclude_if=lambda value: not value
    )
    preferred_groups: tuple[PreferredCompletionGroup, ...] = Field(
        default=(), max_length=16, exclude_if=lambda value: not value
    )
    preferred_next: int = Field(default=0, ge=0, exclude_if=lambda value: not value)

    @model_validator(mode="after")
    def cursor_bounds(self) -> "CompletionSeekCursor":
        if self.observed_classes != tuple(sorted(set(self.observed_classes))):
            raise ValueError("Observed complete classes must be sorted and unique.")
        if self.observed_classes and self.schema_name == "hop.context-group-seek/v4":
            raise ValueError("Hierarchical observed-class scheduling requires a v7 or v8 cursor.")
        if (self.preferred_groups or self.preferred_next) and (
            self.schema_name != "hop.context-group-seek/v8"
        ):
            raise ValueError("Preferred groups require the v8 cursor.")
        if self.preferred_next > len(self.preferred_groups):
            raise ValueError("Preferred progress exceeds its bounded group list.")
        addresses = tuple(group.address for group in self.preferred_groups)
        if len(set(addresses)) != len(addresses):
            raise ValueError("Preferred groups must be distinct.")
        if self.preferred_next and not self.initialized:
            raise ValueError("Preferred progress requires an initialized ordinary frontier.")
        if self.frontier and not self.initialized:
            raise ValueError("An uninitialized cursor cannot contain a frontier.")
        keys = tuple(entry.priority() for entry in self.frontier)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("The frontier must be canonically ordered and contain no duplicates.")
        pending = [
            (e.geometry, e.page, e.group, e.work.pair) for e in self.frontier if e.work is not None
        ]
        if len(pending) != len(set(pending)):
            raise ValueError("A local pair cannot have duplicate pending attempts.")
        return self


class CompletionAttemptCursor(CompletionWork):
    """One pair's next auxiliary word within an exact conditional group."""

    geometry_rank: int = Field(ge=0)
    page: int = Field(ge=0)
    group: int = Field(ge=0)
    depth: int = Field(default=0, ge=0)
    after: CompletionSeekCursor
