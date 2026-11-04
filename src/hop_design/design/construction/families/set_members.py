"""Admit set authorities and bind exact selections before projecting their molecules."""

import json
from pathlib import Path
from typing import Any, NamedTuple

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.family.selection import (
    ConstructionSetMember,
    ConstructionSetRequest,
)

from ..complete.bundle import VerifiedConstructionBundle, load_verified_construction_bundle
from ..public import ConstructionProjection, project_hairpin_portrait
from ..selection_reference import ConstructionSelection, load_construction_selection


class SelectedSetMember(NamedTuple):
    receipt: VerifiedConstructionBundle
    selection: ConstructionSelection
    portrait: ConstructionProjection
    projection: dict[str, Any]


def admit_set_members(
    request: ConstructionSetRequest, base: Path
) -> tuple[dict[str, SelectedSetMember], tuple[ProtectedRoot, ...]]:
    """Standalone requests always load and replay every referenced authority."""
    records = {}
    roots = []
    identities: set[tuple[str, str]] = set()
    for member in request.members:
        root = ProtectedRoot.capture(base / member.bundle_path)
        receipt = load_verified_construction_bundle(root.path)
        root.require_unchanged()
        roots.append(root)
        records[member.name] = _bind_member(base, member, receipt, identities)
    return records, tuple(roots)


def project_set_members(
    request: ConstructionSetRequest,
    base: Path,
    receipts: dict[str, VerifiedConstructionBundle],
) -> dict[str, SelectedSetMember]:
    """Bind saved selections to admitted receipts, including inside a captured discovery."""
    if receipts.keys() != {member.name for member in request.members}:
        raise ValueError("Admitted authorities must match the explicit set members.")
    records = {}
    identities: set[tuple[str, str]] = set()
    for member in request.members:
        records[member.name] = _bind_member(base, member, receipts[member.name], identities)
    return records


def _bind_member(
    base: Path,
    member: ConstructionSetMember,
    receipt: VerifiedConstructionBundle,
    identities: set[tuple[str, str]],
) -> SelectedSetMember:
    selection = load_construction_selection(base / member.selection_path, receipt=receipt)
    identity = (receipt.result_id, selection.materialized_realization_id)
    if identity in identities:
        raise ValueError("Set contains a duplicate exact construction selection.")
    identities.add(identity)
    portrait = project_hairpin_portrait(receipt, materialized_realization_id=identity[1])
    return SelectedSetMember(receipt, selection, portrait, json.loads(portrait.json_bytes))
