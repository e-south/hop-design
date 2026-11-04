"""Continue bounded local witness pairs without changing any molecular request."""

import json
from itertools import product
from pathlib import Path
from typing import Any

from ..execution.candidate import evaluate_candidate
from ..execution.coverage import describe_local_coverage
from ..local_choices import list_local_realizations
from ..local_public import discover_local_neighborhood, load_verified_local_neighborhood
from ..product_request import prepare_construction_request
from ..projection_packet import ConstructionProjection
from ..public import (
    VerifiedConstructionBundle,
    project_hairpin_portrait,
)
from .member_admission import AdmittedMember
from .properties import shared_values


def capture_portrait(
    portrait: ConstructionProjection, root: Path, prefix: str, files: dict[str, bytes]
) -> None:
    directory = portrait.write(root / prefix)
    files.update(
        {
            f"{prefix}/{p.relative_to(directory).as_posix()}": p.read_bytes()
            for p in directory.rglob("*")
            if p.is_file()
        }
    )


def compare_choice(
    receipt: VerifiedConstructionBundle,
    identity: str,
    properties: list[str],
    reference: dict[str, Any],
) -> dict[str, Any]:
    portrait = project_hairpin_portrait(receipt, materialized_realization_id=identity)
    data = json.loads(portrait.json_bytes)
    observed = shared_values(data, properties)
    differences = [p for p in properties if observed[p] != reference[p]]
    return {
        "source_result_id": receipt.result_id,
        "materialized_realization_id": identity,
        "compatible": not differences,
        "differing_properties": differences,
        "geometry": {
            k: data[k] for k in ("loop_nt", "loop_side_paired_bp", "open_side_paired_positions")
        },
    }


def evaluate_member(
    root: Path,
    member: AdmittedMember,
    properties: list[str],
    reference: dict[str, Any],
    remaining: int,
    files: dict[str, bytes],
) -> dict[str, Any]:
    name = member.name
    request = root / "family/members" / name / "request.json"
    inputs = prepare_construction_request(request).write(root / "prepared" / name)
    locals_, choices, coverage, searches = {}, {}, {}, []
    for local in ("foldback", "basal"):
        if not (inputs / (local + ".json")).exists():
            continue
        saved = root / "family/members" / name / "outcome" / local / "result.json"
        if saved.exists():
            receipt = load_verified_local_neighborhood(saved)
        else:
            receipt = discover_local_neighborhood(inputs / (local + ".json"))
            searches.append(local)
        location = receipt.write(root / "locals" / name / local)
        locals_[local] = location / "result.json"
        choices[local] = list_local_realizations(receipt)
        coverage[local] = describe_local_coverage(receipt, local)
        for path in location.rglob("*"):
            if path.is_file():
                files[f"locals/{name}/{local}/{path.relative_to(location).as_posix()}"] = (
                    path.read_bytes()
                )
    count = len(choices["foldback"]) * (len(choices["basal"]) if "basal" in choices else 1)
    original = (
        []
        if member.receipt is None
        else [
            compare_choice(member.receipt, identity, properties, reference)
            for identity in member.receipt.materialized_realization_ids
        ]
    )
    candidates = []
    for ordinal, (foldback, basal) in enumerate(
        product(choices["foldback"], choices.get("basal", (None,)))
    ):
        if ordinal >= remaining:
            break
        prefix = f"candidates/{name}/{ordinal}"
        packet, complete = evaluate_candidate(
            request,
            design_id="matched-" + name,
            locations=locals_,
            foldback=foldback,
            basal=basal,
            output=root / prefix / "outcome",
        )
        files.update({f"{prefix}/outcome/{p}": content for p, content in packet._files})
        summary = json.loads(packet.json_bytes)
        evaluated = []
        if summary["accepted"]:
            for i, identity in enumerate(complete.materialized_realization_ids):
                choice = compare_choice(complete, identity, properties, reference)
                portrait = project_hairpin_portrait(complete, materialized_realization_id=identity)
                capture_portrait(portrait, root, f"{prefix}/choices/{i}", files)
                choice["selection"] = {
                    "bundle_path": f"{prefix}/outcome/construction",
                    "selection_path": f"{prefix}/choices/{i}/selection.json",
                }
                choice["portrait"] = f"{prefix}/choices/{i}/projection.svg"
                choice["preparation"] = f"{prefix}/choices/{i}/preparation/report.md"
                evaluated.append(choice)
        candidates.append(
            {
                "ordinal": ordinal,
                "status": summary["status"],
                "scope": summary["scope"],
                "selected_local_realizations": summary["selected_local_realizations"],
                "rejection_reasons": summary["rejection_reasons"],
                "preparation_constraints": summary.get("preparation_constraints", []),
                "outcome": f"{prefix}/outcome/report.md",
                "choices": evaluated,
            }
        )
    return {
        "name": name,
        "original_choices": original,
        "original_status": member.outcome["status"],
        "local_coverage": coverage,
        "local_searches_run": searches,
        "recorded_pairs": count,
        "evaluated_pairs": len(candidates),
        "unexamined_pairs": count - len(candidates),
        "candidates": candidates,
    }
