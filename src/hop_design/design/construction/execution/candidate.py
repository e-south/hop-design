"""Evaluate one explicit local pair through the ordinary public continuation contract."""

from pathlib import Path

from ..complete.bundle import bind_published_compilation
from ..local_choices import LocalRealizationChoice
from ..public import VerifiedConstructionBundle
from ..request_continuation import continue_construction_request
from ..request_execution import ConstructionRequestExecution


def evaluate_candidate(
    request: Path,
    *,
    design_id: str,
    locations: dict[str, Path],
    foldback: LocalRealizationChoice,
    basal: LocalRealizationChoice | None,
    output: Path,
) -> tuple[ConstructionRequestExecution, VerifiedConstructionBundle]:
    packet = continue_construction_request(
        request,
        design_id=design_id,
        foldback_path=locations["foldback"],
        foldback_realization_id=foldback.realization_id,
        basal_path=locations.get("basal"),
        basal_realization_id=None if basal is None else basal.realization_id,
    )
    packet.write(output)
    if packet._compilation is None:
        raise ValueError("Candidate continuation omitted its construction compilation.")
    return packet, bind_published_compilation(output / "construction", packet._compilation)
