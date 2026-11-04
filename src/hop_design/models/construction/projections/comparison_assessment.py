"""Classify recorded comparison facts without inferring experimental equivalence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from hop_design.models.base import HopModel

if TYPE_CHECKING:
    from .comparison import PropertyComparison


class ComparisonAssessment(HopModel):
    scaffold_status: Literal["comparable", "different_stages", "unavailable"]
    changed_scaffold_fields: tuple[str, ...]
    shared_scaffold_fields: tuple[str, ...]
    shifted_coordinate_fields: tuple[str, ...]
    changed_preparation_fields: tuple[str, ...]
    changed_endpoint_fields: tuple[str, ...]
    non_loop_sequences_conserved: bool | None


_NON_LOOP = (
    "terminal_primary",
    "open_primary",
    "stem_primary",
    "closing_primary",
    "closing_return",
    "stem_return",
    "open_return",
    "terminal_return",
)
_ENDPOINT = {
    "Payload",
    "Requested endpoint",
    "Endpoint topology",
    "Hairpin-encoding sequence",
    "Closing-flank retained sequence (nt)",
    "Attachment-flank retained sequence (nt)",
    "Left cohesive end",
    "Right cohesive end",
}


def assess_comparison(properties: tuple[PropertyComparison, ...]) -> ComparisonAssessment:
    facts = {p.field: p for p in properties}
    available = facts.get("hairpin.availability")
    stage = facts.get("hairpin.stage")
    status: Literal["comparable", "different_stages", "unavailable"] = "unavailable"
    if available and available.left == available.right == "available" and stage:
        status = "different_stages" if stage.changed else "comparable"
    scaffold = [
        p
        for p in properties
        if p.field.startswith("hairpin.")
        and p.field not in {"hairpin.availability", "hairpin.unavailable_reason"}
        and not p.field.endswith(".span")
    ]
    sequences = [facts.get(f"hairpin.region.{r}.sequence") for r in _NON_LOOP]
    conserved = None
    if status == "comparable" and all(
        p is not None and isinstance(p.left, str) and isinstance(p.right, str) for p in sequences
    ):
        conserved = all(p is not None and not p.changed for p in sequences)
    prep: list[str] = []
    endpoint: list[str] = []
    for p in properties:
        if not p.changed or not p.field.startswith("preparation."):
            continue
        label = p.field.removeprefix("preparation.")
        target = endpoint if label in _ENDPOINT or label.startswith("Endpoint strand ") else prep
        target.append(p.field)
    return ComparisonAssessment(
        scaffold_status=status,
        changed_scaffold_fields=tuple(p.field for p in scaffold if p.changed),
        shared_scaffold_fields=tuple(p.field for p in scaffold if not p.changed)
        if status == "comparable"
        else (),
        shifted_coordinate_fields=tuple(
            p.field for p in properties if p.changed and p.field.endswith(".span")
        ),
        changed_preparation_fields=tuple(prep),
        changed_endpoint_fields=tuple(endpoint),
        non_loop_sequences_conserved=conserved,
    )
