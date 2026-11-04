"""Derived inventory facts shared by exploration and saved-packet admission."""

import json
from pathlib import Path
from typing import Any

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..public import VerifiedConstructionBundle, project_hairpin_portrait
from .drawings import complementary_drawings


def require_budget(value: int) -> None:
    if type(value) is not int or not 1 <= value <= 64:
        raise ValueError("max_continuations must be an explicit integer from 1 to 64.")


def pair_design_id(request: bytes, foldback: str, basal: str | None) -> str:
    """Bind exact design naming to intent and witnesses, never budget or display order."""
    return sha256_digest(canonical_json_bytes([json.loads(request), foldback, basal]))[7:]


def describe_options(
    receipt: VerifiedConstructionBundle, folder: Path, *, prefix: str, ordinal: int
) -> list[dict[str, Any]]:
    """Project complete identities into ordinary portraits and explicit selections."""
    options = []
    for index, identity in enumerate(receipt.materialized_realization_ids):
        portrait = project_hairpin_portrait(receipt, materialized_realization_id=identity)
        portrait.write(folder / "choices" / str(index))
        data = json.loads(portrait.json_bytes)
        location = f"{prefix}/choices/{index}"
        for name, content in complementary_drawings(
            receipt,
            identity,
            portrait.json_bytes,
            (folder / "choices" / str(index) / "projection.svg").read_bytes(),
        ).items():
            (folder / "choices" / str(index) / name).write_bytes(content)
        options.append(
            {
                "label": f"option-{ordinal + 1:04d}-{index + 1:02d}",
                "source_result_id": receipt.result_id,
                "materialized_realization_id": identity,
                "stage_role": data["stage_role"],
                "endpoint": data["endpoint"],
                "geometry": HairpinPortraitProjection.model_validate_json(
                    portrait.json_bytes
                ).scaffold_dimensions,
                "selection": {
                    "bundle_path": f"{prefix}/outcome/construction",
                    "selection_path": f"{location}/selection.json",
                },
                "portrait": f"{location}/projection.svg",
                "closing_drawing": f"{location}/closing.svg",
                "product_stages": f"{location}/stages.svg",
                "preparation": f"{location}/preparation/report.md",
            }
        )
    return options


def describe_candidate(
    receipt: VerifiedConstructionBundle, result: dict[str, Any], *, prefix: str, ordinal: int
) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "outcome": f"{prefix}/outcome/report.md",
        **{
            key: result.get(key)
            for key in (
                "status",
                "scope",
                "selected_local_realizations",
                "rejection_reasons",
                "preparation_constraints",
            )
        },
        "accounting": receipt._verified_source().result.accounting.model_dump(mode="json"),
    }


def summarize_options(
    *,
    producer: dict[str, Any],
    request: bytes,
    context: dict[str, Any],
    coverage: dict[str, Any],
    total: int,
    budget: int,
    candidates: list[dict[str, Any]],
    options: list[dict[str, Any]],
    objective: DesignSearchObjective | None = None,
    start_pair: int = 0,
) -> dict[str, Any]:
    return {
        "schema": "hop.construction-options/v2" if start_pair else "hop.construction-options/v1",
        **(
            {"pair_window": {"start": start_pair, "stop": start_pair + len(candidates)}}
            if start_pair
            else {}
        ),
        "producer": producer,
        "request_digest": sha256_digest(request),
        "endpoint": context["endpoint"],
        "requested_ends": context["requested_ends"],
        "local_coverage": coverage,
        "coverage": {
            "max_continuations": budget,
            "recorded_pairs": total,
            "evaluated_pairs": len(candidates),
            "unexamined_pairs": total - len(candidates),
            "completion": "recorded_pairs_examined"
            if len(candidates) == total
            else "stopped_by_bound",
            "global_route_feasibility": "not_assessed",
        },
        "candidates": candidates,
        "options": options,
        "selected_options": [],
        **({"search_objective": objective.model_dump(mode="json")} if objective else {}),
    }
