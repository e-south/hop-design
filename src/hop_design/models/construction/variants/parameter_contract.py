"""Typed teaching and measurement contract used by the parameter registry."""

from typing import Any, Literal

from hop_design.models.base import HopModel

_SYMBOLS = {
    "left_end_word": "wL",
    "left_end_polarity": "pL",
    "left_gap": "gL",
    "right_end_word": "wR",
    "right_end_polarity": "pR",
    "right_gap": "gR",
    "release_method": "eR",
    "basal_method": "eB",
    "basal_strand": "sB",
    "adapter_annealing_min_nt": "aMin",
    "adapter_annealing_achieved_nt": "aObs",
    "noncanonical_pairs": "Nc",
    "open_side_paired_positions": "O",
    "five_prime_unpaired_nt": "t5",
    "three_prime_unpaired_nt": "t3",
    "source_forward_primer_required_nt": "Fmin",
    "source_forward_primer_available_nt": "Fav",
    "foldback_method": "eF",
    "foldback_strand": "sF",
    "loop_word": "W",
    "source_reverse_primer_required_nt": "Rmin",
    "source_reverse_primer_available_nt": "Rav",
}


class ParameterDefinition(HopModel):
    key: str
    canonical_key: str
    label: str
    design_role: Literal["product", "construction", "outcome", "comparison"]
    group: Literal["foldback", "basal", "interfaces", "methods", "scaffold"]
    kind: Literal["numeric", "categorical"]
    stage: str
    neighborhood: str
    measurement: str
    role: Literal["achieved", "required", "derived", "comparison"] = "achieved"
    glyph_frame: Literal["source", "association", "hairpin", "insert", "context"]
    representation: Literal[
        "span", "threshold", "sequence", "contact", "recognition", "orientation", "context"
    ]
    boundaries: tuple[str, str] | None = None
    equivalent_measurements: tuple[str, ...] = ()
    symbol: str = ""
    unit: str = ""
    dependencies: tuple[str, ...] = ()
    relationship: str | None = None
    position_from_ligation: int | None = None


def dimension(
    key: str,
    label: str,
    group: Literal["foldback", "basal", "interfaces", "methods", "scaffold"],
    stage: str,
    region: str,
    measurement: str,
    unit: str = "nt",
    symbol: str = "",
    **kwargs: Any,
) -> ParameterDefinition:
    return ParameterDefinition(
        key=key,
        canonical_key=kwargs.pop("canonical_key", key),
        design_role=kwargs.pop("design_role", "construction"),
        label=label,
        group=group,
        kind="numeric",
        stage=stage,
        neighborhood=region,
        measurement=measurement,
        unit=unit,
        symbol=symbol or _SYMBOLS.get(key, ""),
        glyph_frame=kwargs.pop("glyph_frame", _frame(stage)),
        representation=kwargs.pop("representation", "span"),
        **kwargs,
    )


def category(
    key: str,
    label: str,
    group: Literal["foldback", "basal", "interfaces", "methods", "scaffold"],
    stage: str,
    region: str,
    measurement: str,
    **kwargs: Any,
) -> ParameterDefinition:
    return ParameterDefinition(
        key=key,
        canonical_key=kwargs.pop("canonical_key", key),
        design_role=kwargs.pop("design_role", "construction"),
        label=label,
        group=group,
        kind="categorical",
        stage=stage,
        neighborhood=region,
        measurement=measurement,
        glyph_frame=kwargs.pop("glyph_frame", _frame(stage)),
        representation=kwargs.pop("representation", "context"),
        symbol=kwargs.pop("symbol", _SYMBOLS.get(key, "")),
        **kwargs,
    )


def _frame(stage: str) -> str:
    return {
        "source_duplex": "source",
        "source_adapter_association": "association",
        "hairpin": "hairpin",
        "folded": "hairpin",
        "released_insert": "insert",
        "preparation": "context",
        "comparison_stage": "context",
    }[stage]
