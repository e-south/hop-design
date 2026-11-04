"""Declared molecular comparison, separate from exact identity and preparation history."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.serialization import canonical_json_bytes, sha256_digest

Count = Annotated[int, Field(ge=0)]
ShapeKey = Literal[
    "loop_nt",
    "loop_side_paired_bp",
    "open_side_paired_positions",
    "five_prime_unpaired_nt",
    "three_prime_unpaired_nt",
    "left_gap",
    "right_gap",
    "five_prime_retained_tail_nt",
    "three_prime_retained_tail_nt",
]
SequenceKey = Literal[
    "loop", "basal_pairs", "foldback_pairs", "five_prime_retained_tail", "three_prime_retained_tail"
]
InterfaceKey = Literal["left_word", "right_word", "left_polarity", "right_polarity"]
SHAPE_KEYS = (
    "loop_nt",
    "loop_side_paired_bp",
    "open_side_paired_positions",
    "five_prime_unpaired_nt",
    "three_prime_unpaired_nt",
)


class MolecularDescriptor(HopModel):
    identity: str = Field(min_length=1)
    stem: str = Field(min_length=1, pattern="^[ACGT]+$")
    endpoint: Literal[
        "ssdna_hairpin", "adapter_ligated_hairpin", "hairpin_pcr_duplex", "clone_ready_duplex"
    ]
    shape: dict[ShapeKey, Count]
    sequences: dict[SequenceKey, tuple[str, ...] | tuple[tuple[str, str, str], ...]]
    interfaces: dict[InterfaceKey, str] | None = None
    retained_terminal_bases: dict[Literal["five_prime", "three_prime"], tuple[str, ...]] | None = (
        Field(default=None, exclude_if=lambda value: value is None)
    )

    @model_validator(mode="after")
    def consistent_regions(self) -> Self:
        released = self.endpoint == "clone_ready_duplex"
        expected = {*SHAPE_KEYS, *(["left_gap", "right_gap"] if released else [])}
        if self.shape.keys() != expected:
            raise ValueError("Molecular comparison requires all applicable shape measurements.")
        if self.sequences.keys() != {"loop", "basal_pairs", "foldback_pairs"}:
            raise ValueError("Molecular comparison requires all retained sequence regions.")
        for key, values in self.sequences.items():
            if key == "loop":
                if not values or any(
                    type(v) is not str or len(v) != 1 or v not in "ACGT" for v in values
                ):
                    raise ValueError("The compared loop requires exact individual bases.")
            elif any(
                type(v) is not tuple
                or len(v) != 3
                or v[0] not in ("A", "C", "G", "T")
                or v[1] not in ("A", "C", "G", "T")
                or not v[2]
                for v in values
            ):
                raise ValueError("Compared contacts require two oriented bases and a class.")
        lengths: tuple[tuple[SequenceKey, ShapeKey], ...] = (
            ("loop", "loop_nt"),
            ("basal_pairs", "open_side_paired_positions"),
            ("foldback_pairs", "loop_side_paired_bp"),
        )
        for sequence, shape in lengths:
            if len(self.sequences[sequence]) != self.shape[shape]:
                raise ValueError(f"The {sequence} sequence must agree with its shape measurement.")
        if released:
            if self.interfaces is None or self.interfaces.keys() != {
                "left_word",
                "right_word",
                "left_polarity",
                "right_polarity",
            }:
                raise ValueError("Released products require both recorded interfaces.")
            for side in ("left", "right"):
                word = self.interfaces[f"{side}_word"]  # type: ignore[index]
                if not word or set(word) - set("ACGT"):
                    raise ValueError("Compared interfaces require exact end words.")
                if self.interfaces[f"{side}_polarity"] not in {"five_prime", "three_prime"}:  # type: ignore[index]
                    raise ValueError("Compared interfaces require recorded end polarity.")
        elif self.interfaces is not None:
            raise ValueError("Receiving interfaces do not apply before released inserts.")
        if self.retained_terminal_bases is not None:
            if not released:
                raise ValueError("Retained terminal comparison applies only to released inserts.")
            if self.retained_terminal_bases.keys() != {"five_prime", "three_prime"}:
                raise ValueError("Retained terminal comparison requires both hairpin termini.")
            for side, bases in self.retained_terminal_bases.items():
                if len(bases) > self.shape[f"{side}_unpaired_nt"] or any(  # type: ignore[index]
                    base not in {"A", "C", "G", "T"} for base in bases
                ):
                    raise ValueError("Retained terminal bases must fit the exact hairpin tail.")
        return self

    @property
    def compared_shape(self) -> dict[ShapeKey, int]:
        shape = dict(self.shape)
        for side, bases in (self.retained_terminal_bases or {}).items():
            del shape[f"{side}_unpaired_nt"]  # type: ignore[arg-type]
            shape[f"{side}_retained_tail_nt"] = len(bases)  # type: ignore[index]
        return shape

    @property
    def compared_sequences(
        self,
    ) -> dict[SequenceKey, tuple[str, ...] | tuple[tuple[str, str, str], ...]]:
        sequences = dict(self.sequences)
        for side, bases in (self.retained_terminal_bases or {}).items():
            sequences[f"{side}_retained_tail"] = bases  # type: ignore[index]
        return sequences

    @property
    def scope_key(self) -> str:
        scope = [self.stem, self.endpoint]
        if self.retained_terminal_bases is not None:
            scope.append("retained_terminals/v1")
        return sha256_digest(canonical_json_bytes(scope))

    @property
    def comparison_key(self) -> str:
        """Equal compared features do not establish complete molecular identity."""
        if self.retained_terminal_bases is None:
            return sha256_digest(canonical_json_bytes(self.model_dump(exclude={"identity"})))
        return sha256_digest(
            canonical_json_bytes(
                {
                    "stem": self.stem,
                    "endpoint": self.endpoint,
                    "terminal_scope": "retained_terminals/v1",
                    "shape": self.compared_shape,
                    "sequences": self.compared_sequences,
                    "interfaces": self.interfaces,
                }
            )
        )


class MolecularDistancePolicy(HopModel):
    """Explicit comparison choices; defaults describe the original distance."""

    schema_id: Literal["hop.molecular-distance/v1"] = Field(
        default="hop.molecular-distance/v1", alias="schema"
    )
    regional_metric: Literal["length_adjusted_edit", "normalized_edit"] = "length_adjusted_edit"
    end_word_metric: Literal["normalized_edit", "hamming"] = "normalized_edit"
    numeric_scaling: Literal["observed_range", "declared"] = "observed_range"
    declared_scales: dict[ShapeKey, Annotated[int, Field(gt=0)]] = Field(default_factory=dict)
    constant_features: Literal["omit"] = "omit"
    contact_tokens: Literal["oriented_base_pair_and_class"] = "oriented_base_pair_and_class"

    @model_validator(mode="after")
    def explicit_scales(self) -> Self:
        if (self.numeric_scaling == "declared") != bool(self.declared_scales):
            raise ValueError(
                "Declared scaling requires declared scales; observed scaling forbids them."
            )
        return self

    def validate_end_lengths(self, rows: tuple[MolecularDescriptor, ...]) -> None:
        """A fixed-register comparison must never silently truncate an end word."""
        if self.end_word_metric == "hamming":
            for key in ("left_word", "right_word"):
                if len({len((r.interfaces or {}).get(key, "")) for r in rows}) > 1:
                    raise ValueError(
                        "Hamming end comparison requires equal word lengths within each side."
                    )


class MolecularComparisonBasis(HopModel):
    schema_id: Literal["hop.molecular-comparison/v1", "hop.molecular-comparison/v2"] = Field(
        default="hop.molecular-comparison/v1", alias="schema"
    )
    scope_key: str
    comparison_keys: tuple[str, ...] = Field(min_length=1)
    shape_scales: dict[ShapeKey, Annotated[int, Field(gt=0)]]
    sequence_keys: tuple[SequenceKey, ...]
    interface_keys: tuple[InterfaceKey, ...]
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0)
    distance_policy: MolecularDistancePolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @property
    def effective_policy(self) -> MolecularDistancePolicy:
        """Legacy records retain their original arithmetic without rewriting bytes."""
        return self.distance_policy or MolecularDistancePolicy()

    @model_validator(mode="after")
    def valid_weights(self) -> Self:
        from math import isfinite

        if any(not isfinite(w) or w <= 0 for w in self.weights):
            raise ValueError("Each comparison block requires a finite positive weight.")
        if len(set(self.comparison_keys)) != len(self.comparison_keys):
            raise ValueError("Comparison members must be distinct feature signatures.")
        if self.schema_id == "hop.molecular-comparison/v1":
            if any("retained_tail" in key for key in (*self.shape_scales, *self.sequence_keys)):
                raise ValueError("Retained terminal features require molecular-comparison/v2.")
        elif {"five_prime_unpaired_nt", "three_prime_unpaired_nt"} & self.shape_scales.keys():
            raise ValueError("Version 2 compares retained terminals, not complete tail lengths.")
        if (
            self.distance_policy
            and self.distance_policy.numeric_scaling == "declared"
            and any(
                self.distance_policy.declared_scales.get(k) != v
                for k, v in self.shape_scales.items()
            )
        ):
            raise ValueError("Effective shape scales disagree with the declared policy.")
        return self


class MolecularDissimilarity(HopModel):
    """Explanatory block differences; not folding, function or compatibility evidence."""

    shape: float | None
    sequence: float | None
    interface: float | None
    total: float = Field(ge=0, le=1)
