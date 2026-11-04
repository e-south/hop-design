"""Return explicitly continued results to a new, portable family capture."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from hop_design.design.runtime import producer_identity
from hop_design.design.source_documents import _read_source_bytes, load_source_mapping
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.family.request import ConstructionFamilyRequest
from hop_design.serialization import sha256_digest

from ..public import project_hairpin_portrait
from .admission import admit_family
from .capture import capture_family, write_snapshot
from .choices import FAMILY_INTERPRETATION, describe_choice
from .member_admission import _equal, admit_member
from .packet import SourceBoundFamilyPacket
from .prepare import prepare_construction_family
from .properties import shared_values
from .revision import FamilyRevision


@dataclass(frozen=True, init=False, repr=False)
class ReconciledConstructionFamily(SourceBoundFamilyPacket):
    """Admitted family revision retaining its original and continued authorities."""


def _capture_outcome(path: str | Path) -> tuple[ProtectedRoot, dict[str, bytes]]:
    root = ProtectedRoot.capture(Path(path))
    paths = tuple(root.path.rglob("*"))
    if len(paths) > 20_000 or any(p.is_symlink() for p in paths):
        raise ValueError("Outcome inventory exceeds its bound or contains a symlink.")
    files, size = {}, 0
    for p in sorted(paths):
        if p.is_dir():
            continue
        content = _read_source_bytes(
            p, max_bytes=max(1, 512 * 1024 * 1024 - size), source_label="Outcome artifact"
        )
        size += len(content)
        if size > 512 * 1024 * 1024:
            raise ValueError("Outcome exceeds 512 MiB.")
        files[p.relative_to(root.path).as_posix()] = content
    root.require_unchanged()
    return root, files


def reconcile_construction_family(
    path: str | Path,
    *,
    source_member: str,
    outcome_path: str | Path,
    member: str | None = None,
    revised_request: str | Path | None = None,
    preferred_loop_nt: int | None = None,
) -> ReconciledConstructionFamily:
    """Admit one exact continuation; an edited alternative needs a new named member."""
    if preferred_loop_nt is not None and (
        type(preferred_loop_nt) is not int or preferred_loop_nt < 3
    ):
        raise ValueError("The declared loop preference must be an integer of at least 3 nt.")
    producer = producer_identity()
    parent_root, parent_files = capture_family(path)
    outcome_root, incoming = _capture_outcome(outcome_path)
    target = member or source_member
    with tempfile.TemporaryDirectory(prefix="hop-family-reconcile-") as temporary:
        root = Path(temporary)
        parent_path = root / "parent"
        write_snapshot(parent_files, parent_path)
        parent, _ = admit_family(parent_path)
        old_members = {m["name"]: m for m in parent["members"]}
        if source_member not in old_members:
            raise ValueError("Source member does not belong to the saved family.")
        prepared = prepare_construction_family(revised_request or parent_path / "family.json")
        preview = json.loads(prepared.json_bytes)
        if not preview["executable"]:
            raise ValueError("Revised family contains request conflicts.")
        family = ConstructionFamilyRequest.model_validate_json(dict(prepared._files)["family.json"])
        names = {m.name for m in family.members}
        edited = target != source_member
        if names != (set(old_members) | {target}) or target not in names:
            raise ValueError("Revised roster must preserve all original members.")
        if edited and (target in old_members or revised_request is None):
            raise ValueError(
                "Edited requests require a new member and explicit revised family request."
            )
        files = {
            k: v
            for k, v in prepared._files
            if k not in {"manifest.json", "summary.json", "report.md"}
        }
        for name in old_members:
            _equal(
                files[f"members/{name}/request.json"],
                parent_files[f"members/{name}/request.json"],
                "retained request",
            )
        _equal(
            incoming.get("inputs/request.json"),
            files[f"members/{target}/request.json"],
            "continued input request",
        )
        if (
            edited
            and files[f"members/{target}/request.json"]
            == parent_files[f"members/{source_member}/request.json"]
        ):
            raise ValueError("An edited request must differ from its source request.")
        for local in preview["members"]:
            name = local["name"]
            prefix = f"members/{name}/outcome/"
            capture = (
                incoming
                if name == target
                else {
                    k.removeprefix(prefix): v
                    for k, v in parent_files.items()
                    if k.startswith(prefix)
                }
            )
            files.update({prefix + k: v for k, v in capture.items()})
        snapshot = root / "revised"
        write_snapshot(files, snapshot)
        rows, display = [], []
        reference = None
        for local in preview["members"]:
            name = local["name"]
            prefix = f"members/{name}"
            outcome = load_source_mapping(snapshot / prefix / "outcome/summary.json")
            proof = admit_member(
                snapshot / prefix,
                name,
                local,
                {leaf: files[f"{prefix}/{leaf}"] for leaf in ("request.json", "construction.json")},
                producer=outcome["producer"],
                continuation=outcome["continuation"],
                external_design_id=True,
            )
            row = {"name": name, "outcome": proof.outcome, "choices": []}
            if proof.receipt is not None:
                for ordinal, identity in enumerate(proof.receipt.materialized_realization_ids):
                    portrait = project_hairpin_portrait(
                        proof.receipt, materialized_realization_id=identity
                    )
                    data = json.loads(portrait.json_bytes)
                    values = shared_values(data, family.shared_properties)
                    if reference is None:
                        reference = {"member": name, "properties": values}
                    choice = describe_choice(
                        name, ordinal, data, family.shared_properties, reference["properties"]
                    )
                    row["choices"].append(choice)
                    folder = portrait.write(snapshot / prefix / "choices" / str(ordinal))
                    files.update(
                        {
                            f"{prefix}/choices/{ordinal}/"
                            + p.relative_to(folder).as_posix(): p.read_bytes()
                            for p in folder.rglob("*")
                            if p.is_file()
                        }
                    )
                    if not choice["shared_property_differences"]:
                        order = tuple(
                            (1 if p.direction == "ascending" else -1) * values[p.dimension]
                            for p in family.display_preferences
                        )
                        display.append((order, name, identity))
            rows.append(row)
        revision = FamilyRevision(
            kind="edited-request" if edited else "continuation",
            source_member=source_member,
            target_member=target,
            parent_manifest_digest=sha256_digest(parent_files["manifest.json"]),
            prior_status=old_members[source_member]["outcome"]["status"],
            preferred_loop_nt=preferred_loop_nt,
        )
        choices = [
            {"member": name, "materialized_realization_id": identity}
            for _, name, identity in sorted(display)
        ]
        summary = {
            "schema": "hop.construction-family-result/v2",
            "family_id": preview["family_id"],
            "producer": producer,
            "continuation": "reconciled",
            "upper_bounds": preview["upper_bounds"],
            "members": rows,
            "shared_properties": list(family.shared_properties),
            "shared_reference": reference,
            "display_preferences": preview["display_preferences"],
            "display_choices": choices,
            "display_order": list(dict.fromkeys(c["member"] for c in choices)),
            "interpretation": FAMILY_INTERPRETATION,
            "revision": revision.model_dump(mode="json"),
        }
        files.update({"history/parent/" + k: v for k, v in parent_files.items()})
        if len(files) > 20_000 or sum(map(len, files.values())) > 512 * 1024 * 1024:
            raise ValueError("Revised family exceeds the bounded packet inventory.")
        packet = ReconciledConstructionFamily._create(
            files,
            summary,
            "# Revised scaffold family\n\nOriginal requests and outcomes: history/parent/.\n",
        )
        check = root / "check"
        write_snapshot(dict(packet._files), check)
        admit_family(check)
    if producer_identity() != producer:
        raise ValueError("HOP producer changed during family reconciliation.")
    object.__setattr__(packet, "_roots", (parent_root, outcome_root))
    return packet
