"""Explicit edits to generating permissions, distinct from product and query controls."""

from typing import Any, Literal

from pydantic import Field, JsonValue, model_validator

from hop_design.models.base import HopModel

type EnvelopeKind = Literal["integers", "integer", "words", "choice", "methods", "records"]


class EnvelopeField(HopModel):
    path: str
    label: str
    group: str
    kind: EnvelopeKind
    axis: str | None = None
    nullable: bool = False
    unrestricted: Literal["none", "empty", "null"] = "none"
    choices: tuple[str, ...] = ()


def _geometry(region: str, name: str, label: str, kind: EnvelopeKind, **kw: Any) -> EnvelopeField:
    return EnvelopeField(
        path=f"product.{region}.geometry.{name}", label=label, group=region, kind=kind, **kw
    )


# The paths are also the public preview vocabulary. Never accept arbitrary JSON
# patches: supplied stem, receiving ends, exact materials and controls are locked.
ENVELOPE_FIELDS = (
    _geometry(
        "foldback",
        "annealing_arm_lengths_bp",
        "Permitted foldback arms A (bp)",
        "integers",
        axis="foldback_arm_bp",
        unrestricted="empty",
    ),
    _geometry(
        "foldback",
        "junction_offsets_nt",
        "Permitted join displacements D (nt)",
        "integers",
        axis="join_offset_nt",
    ),
    _geometry(
        "foldback",
        "loop_lengths_nt",
        "Permitted loop lengths C (nt)",
        "integers",
        axis="loop_nt",
        unrestricted="empty",
    ),
    _geometry(
        "foldback",
        "loop_sequences",
        "Permitted loop words",
        "words",
        axis="loop_word",
        nullable=True,
        unrestricted="null",
    ),
    _geometry(
        "foldback",
        "minimum_annealing_arm_length_bp",
        "Minimum foldback arm (bp)",
        "integer",
        axis="foldback_arm_bp",
    ),
    _geometry(
        "foldback", "minimum_loop_length_nt", "Minimum loop length (nt)", "integer", axis="loop_nt"
    ),
    *tuple(
        _geometry(
            r,
            "nick_strand",
            "Permitted nick strand",
            "choice",
            axis=f"{r}_strand",
            choices=("top", "bottom", "any"),
        )
        for r in ("foldback", "basal")
    ),
    _geometry(
        "basal",
        "nick_offsets_nt",
        "Permitted basal nick displacements n (nt)",
        "integers",
        axis="basal_nick_offset_nt",
    ),
    _geometry(
        "basal",
        "minimum_adapter_annealing_nt",
        "Required adapter annealing (nt)",
        "integer",
        axis="adapter_annealing_min_nt",
        nullable=True,
    ),
    _geometry(
        "basal",
        "max_noncanonical_pairs",
        "Maximum noncanonical contacts",
        "integer",
        axis="noncanonical_pairs",
    ),
    _geometry(
        "basal", "pairing_constraints", "Positional bases and pairing permissions", "records"
    ),
    EnvelopeField(
        path="end_placements",
        label="Joint left/right end-to-stem gaps (bp)",
        group="interfaces",
        kind="records",
        nullable=True,
    ),
    EnvelopeField(
        path="preparation_changes.basal_nick_enzyme_ids",
        label="Permitted basal nickases",
        group="methods",
        kind="methods",
        axis="basal_method",
        nullable=True,
    ),
    EnvelopeField(
        path="preparation_changes.release_enzyme_ids",
        label="Permitted release enzymes",
        group="methods",
        kind="methods",
        axis="release_method",
        nullable=True,
    ),
    EnvelopeField(
        path="product.foldback.enzymes.allowed_enzyme_ids",
        label="Permitted foldback enzymes",
        group="methods",
        kind="methods",
        axis="foldback_method",
    ),
    EnvelopeField(
        path="product.foldback.enzymes.role_restrictions",
        label="Foldback enzyme roles",
        group="methods",
        kind="records",
    ),
    EnvelopeField(
        path="preparation_changes.adapter_redesign",
        label="Adapter redesign permission",
        group="preparation",
        kind="choice",
        choices=("preserve", "allow"),
    ),
    EnvelopeField(
        path="preparation_changes.three_prime_tail_sequences",
        label="Permitted 3-prime tails",
        group="preparation",
        kind="words",
        nullable=True,
    ),
    EnvelopeField(
        path="parameters",
        label="Inherited parameter restrictions",
        group="requirements",
        kind="records",
    ),
    *tuple(
        EnvelopeField(
            path=f"product.{region}.search.{name}",
            label=f"{region.title()} {label.lower()}",
            group="bounds",
            kind="integer",
        )
        for region in ("foldback", "basal")
        for name, label in (
            ("max_retained_overhead_nt", "Retained construction budget (nt)"),
            ("max_search_nodes", "Maximum local search nodes"),
            ("max_realizations", "Maximum local realizations"),
            ("result_quota", "Local result quota"),
        )
    ),
)


class EnvelopeChange(HopModel):
    path: str
    value: JsonValue

    @model_validator(mode="after")
    def editable_path(self) -> "EnvelopeChange":
        if self.path not in {f.path for f in ENVELOPE_FIELDS}:
            raise ValueError(f"{self.path} is not an editable envelope field.")
        return self


class ScaffoldEnvelopeRevision(HopModel):
    schema_id: Literal["hop.scaffold-envelope-revision/v1"] = Field(alias="schema")
    changes: tuple[EnvelopeChange, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def distinct_fields(self) -> "ScaffoldEnvelopeRevision":
        if len({c.path for c in self.changes}) != len(self.changes):
            raise ValueError("An envelope field may be revised only once per preview.")
        return self
