"""Verify revision ancestry and preserve the distinction between continuation and request edit."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.serialization import sha256_digest

from .capture import capture_family
from .member_admission import _equal


class FamilyRevision(HopModel):
    kind: Literal["continuation", "edited-request"]
    source_member: str
    target_member: str
    parent_manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prior_status: str
    preferred_loop_nt: int | None = Field(default=None, ge=3)


def validate_revision(root: Path, recorded: dict[str, Any], depth: int) -> None:
    from .admission import admit_family

    if depth >= 16:
        raise ValueError("Family revision ancestry exceeds 16 revisions.")
    revision = FamilyRevision.model_validate_json(json.dumps(recorded["revision"]))
    parent_root = root / "history/parent"
    _, snapshot = capture_family(parent_root)
    _equal(
        sha256_digest(snapshot["manifest.json"]), revision.parent_manifest_digest, "parent digest"
    )
    parent, _ = admit_family(parent_root, depth=depth + 1)
    before = {m["name"]: m for m in parent["members"]}
    after = {m["name"]: m for m in recorded["members"]}
    if revision.source_member not in before or revision.target_member not in after:
        raise ValueError("Revision must identify its original and resulting members.")
    _equal(
        revision.prior_status, before[revision.source_member]["outcome"]["status"], "prior status"
    )
    source = snapshot[f"members/{revision.source_member}/request.json"]
    target = (root / f"members/{revision.target_member}/request.json").read_bytes()
    if revision.kind == "continuation":
        _equal(revision.source_member, revision.target_member, "continued member")
        _equal(source, target, "continued request")
        _equal(set(before), set(after), "continued roster")
    else:
        if revision.target_member in before or source == target:
            raise ValueError("An edited request requires a new member and a changed request.")
        _equal(set(after), {*before, revision.target_member}, "edited roster")
    for name, member in before.items():
        if name == revision.target_member:
            continue
        _equal(
            (root / f"members/{name}/request.json").read_bytes(),
            snapshot[f"members/{name}/request.json"],
            "retained request",
        )
        _equal(after[name]["outcome"], member["outcome"], "retained outcome")
    if after[revision.target_member]["outcome"]["accepted"] < 1:
        raise ValueError("Reconciliation requires a complete accepted continuation.")
