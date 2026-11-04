"""Execute a finite roster without discarding failed or unresolved member requests."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from hop_design.design.runtime import producer_identity
from hop_design.models.construction.family.request import ConstructionFamilyRequest

from ..public import load_verified_construction_bundle, project_hairpin_portrait
from ..request_execution import execute_construction_request
from .choices import FAMILY_INTERPRETATION, describe_choice
from .packet import FamilyPacket
from .prepare import prepare_construction_family
from .properties import shared_values


@dataclass(frozen=True, init=False, repr=False)
class ConstructionFamilyExecution(FamilyPacket):
    """All named outcomes and complete choices, with bounded-search scope intact."""


def execute_construction_family(
    path: str | Path, *, continuation: Literal["sole-witness"]
) -> ConstructionFamilyExecution:
    if continuation != "sole-witness":
        raise ValueError("Family execution requires explicit sole-witness continuation.")
    prepared = prepare_construction_family(path)
    preview = json.loads(prepared.json_bytes)
    if not preview["executable"]:
        conflicts = "; ".join(
            f"{m['name']}: {m['conflict']}" for m in preview["members"] if m["conflict"]
        )
        raise ValueError("Family request conflicts must be resolved before execution: " + conflicts)
    # Use the one admitted source snapshot, not a second read of a mutable input.
    files = dict(prepared._files)
    family = ConstructionFamilyRequest.model_validate_json(files["family.json"])
    producer = producer_identity()
    rows: list[dict[str, Any]] = []
    baseline: dict[str, Any] | None = None
    display = []
    with tempfile.TemporaryDirectory(prefix="hop-family-") as temporary:
        root = prepared.write(Path(temporary) / "family")
        for member in family.members:
            folder = root / "members" / member.name
            execution = execute_construction_request(
                folder / "request.json",
                design_id="family-" + member.name,
                continuation=continuation,
            )
            execution.write(folder / "outcome")
            outcome = json.loads(execution.json_bytes)
            row: dict[str, Any] = {"name": member.name, "outcome": outcome, "choices": []}
            if outcome["accepted"]:
                receipt = load_verified_construction_bundle(folder / "outcome/construction")
                for ordinal, selected in enumerate(receipt.materialized_realization_ids):
                    packet = project_hairpin_portrait(receipt, materialized_realization_id=selected)
                    portrait = json.loads(packet.json_bytes)
                    choice_path = folder / "choices" / str(ordinal)
                    packet.write(choice_path)
                    values = shared_values(portrait, family.shared_properties)
                    if baseline is None:
                        baseline = {"member": member.name, "properties": values}
                    choice = describe_choice(
                        member.name,
                        ordinal,
                        portrait,
                        family.shared_properties,
                        baseline["properties"],
                    )
                    differences = choice["shared_property_differences"]
                    row["choices"].append(choice)
                    if not differences:
                        preference = tuple(
                            (1 if p.direction == "ascending" else -1) * values[p.dimension]
                            for p in family.display_preferences
                        )
                        display.append((preference, member.name, selected))
            rows.append(row)
        if producer_identity() != producer:
            raise ValueError("HOP producer changed during family execution.")
        # Finite packet allocation is bounded independently of search coverage.
        files = {}
        size = 0
        for file in sorted(root.rglob("*")):
            if file.is_file():
                size += file.stat().st_size
                if size > 512 * 1024 * 1024:
                    raise ValueError(
                        "Family artifacts exceed the 512 MiB packet limit; narrow the roster."
                    )
                files[file.relative_to(root).as_posix()] = file.read_bytes()
    choices = [
        {"member": name, "materialized_realization_id": selected}
        for _, name, selected in sorted(display)
    ]
    summary: dict[str, object] = {
        "schema": "hop.construction-family-result/v1",
        "family_id": preview["family_id"],
        "producer": producer,
        "continuation": continuation,
        "upper_bounds": preview["upper_bounds"],
        "members": rows,
        "shared_properties": list(family.shared_properties),
        "shared_reference": baseline,
        "display_preferences": preview["display_preferences"],
        "display_choices": choices,
        "display_order": list(dict.fromkeys(c["member"] for c in choices)),
        "interpretation": FAMILY_INTERPRETATION,
    }
    report = [
        "# Scaffold family",
        "",
        "Inspect the complete molecular alternatives, then select explicit members.",
        "",
    ]
    for row in rows:
        outcome = row["outcome"]
        report.append(
            f"- {row['name']}: {outcome['status']} ({outcome['stage']}); "
            f"{len(row['choices'])} complete choices."
        )
    report += [
        "",
        str(summary["interpretation"]),
        "",
        (
            "Each member has its own preparation. No pooled reaction or "
            "experimental performance is established."
        ),
        "",
    ]
    return ConstructionFamilyExecution._create(files, summary, "\n".join(report))
