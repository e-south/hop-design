"""Allocate a declared family budget to existing exact-member discovery engines."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from hop_design.export.publication import publish_directory_create_only
from hop_design.serialization import canonical_json_bytes

from ...intents.base import DesignChoices
from ...intents.resolve import ResolvedDesignRequest, resolve_design_request
from ...packets.capture import capture_packet
from ...packets.publication import ConstructionPacket
from .preview import admit_preview


class FamilyBatch(ConstructionPacket):
    _packet_schema = "hop.design-family-batch/v1"


def batches(root: Path, preview: dict[str, Any]) -> tuple[int, bool]:
    used = 0
    pending = False
    names = {m["name"] for m in preview["members"]}
    for path in sorted((root / "batches").glob("*")):
        _, files = capture_packet(path, schema="hop.design-family-batch/v1")
        batch = json.loads(files["summary.json"])
        if batch["request_digest"] != preview["request_digest"]:
            raise ValueError("Execution batch belongs to another family request.")
        quotas = batch["member_evaluations"]
        if not set(quotas) <= names or any(type(n) is not int or n < 1 for n in quotas.values()):
            raise ValueError("Invalid family execution allocation.")
        used += sum(quotas.values())
        pending |= not (root / "completed" / path.name).is_file()
    if used > preview["max_total_evaluations"]:
        raise ValueError("Saved family exceeds max_total_evaluations.")
    return used, pending


def start_family(
    resolved: ResolvedDesignRequest,
    destination: str | Path,
    *,
    max_evaluations: int,
    effort: dict[str, Any] | None,
    first_choices: int | None,
    objective: dict[str, Any] | None,
) -> DesignChoices:
    from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits

    from ...intents.execute import _DEFAULT_EFFORT, _validate_execution

    preview = json.loads(resolved.json_bytes)
    if max_evaluations > preview["max_total_evaluations"]:
        raise ValueError(
            "Execution exceeds max_total_evaluations; revise the family bound explicitly."
        )
    policy = {**(effort or _DEFAULT_EFFORT.model_dump(mode="json"))}
    if objective is not None:
        policy["objective"] = objective
    limits = SurveyEvaluationLimits.model_validate_json(canonical_json_bytes(policy))
    for member in preview["members"]:
        _validate_execution(
            resolve_design_request(member["request"]),
            limits,
            first_choices=first_choices,
            default_effort=effort is None,
        )
    root = Path(destination)
    # Publish the captured permissions atomically before any member is evaluated.
    files = {"intent/" + name: data for name, data in resolved._files}
    files["policy.json"] = canonical_json_bytes({"effort": effort, "objective": objective})
    packet = ResolvedDesignRequest._create(files, preview, resolved.report_text)
    object.__setattr__(packet, "_roots", resolved._roots)
    if root.exists() or root.is_symlink():
        raise FileExistsError(f"Refusing to replace family discovery: {root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".hop-family-", dir=root.parent))
    try:
        packet.write(staging / "family")
        publish_directory_create_only(staging, root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return continue_family(root, max_evaluations=max_evaluations, first_choices=first_choices)


def continue_family(
    root: Path, *, max_evaluations: int, first_choices: int | None
) -> DesignChoices:
    from ...intents.execute import continue_design_discovery, discover_designs
    from .choices import load_family

    preview = admit_preview(root)
    used, pending = batches(root, preview)
    if pending:
        raise ValueError(
            "An interrupted family batch has reserved work. "
            "Inspect its members before starting a revised family."
        )
    if used + max_evaluations > preview["max_total_evaluations"]:
        raise ValueError(
            "Execution exceeds max_total_evaluations; revise the family bound explicitly."
        )
    members = preview["members"]
    allocation: dict[str, int] = {}
    for offset in range(max_evaluations):
        name = members[(used + offset) % len(members)]["name"]
        allocation[name] = allocation.get(name, 0) + 1
    ordinal = len(list((root / "batches").glob("*")))
    label = f"{ordinal:04d}"
    batch = FamilyBatch._create(
        {},
        {
            "request_digest": preview["request_digest"],
            "member_evaluations": allocation,
            "first_choices": first_choices,
        },
        "# Reserved family evaluations\n",
    )
    batch.write(root / "batches" / label)
    policy = json.loads((root / "family/policy.json").read_bytes())
    for member in members:
        name = member["name"]
        if name not in allocation:
            continue
        directory = root / "members" / name
        if directory.exists():
            continue_design_discovery(
                directory, max_evaluations=allocation[name], first_choices=first_choices
            )
        else:
            discover_designs(
                member["request"],
                directory,
                max_evaluations=allocation[name],
                first_choices=first_choices,
                **policy,
            )
    (root / "completed").mkdir(exist_ok=True)
    (root / "completed" / label).write_bytes(
        canonical_json_bytes({"request_digest": preview["request_digest"]})
    )
    return load_family(root)
