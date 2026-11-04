"""Bind explicit choices to the exact edit revision before ordinary molecular admission."""

import json
from pathlib import Path

from hop_design.models.construction.stage_controls import ResolvedStageControl
from hop_design.serialization import canonical_json_bytes

from ..discovery.selection import _select_captured_scaffold_options
from ..families.selection import ConstructionSet
from .admission import captured_molecular_edit


def select_molecular_edit(
    path: str | Path,
    *,
    edit_digest: str,
    members: dict[str, str],
    baseline: str,
    shared_properties: tuple[str, ...] = (),
    compared_properties: tuple[str, ...] = (),
    stage_controls: tuple[ResolvedStageControl, ...] = (),
) -> ConstructionSet:
    with captured_molecular_edit(path, edit_digest=edit_digest) as admitted:
        captured, _, files, protected = admitted
        selected = _select_captured_scaffold_options(
            *captured,
            members=members,
            baseline=baseline,
            shared_properties=shared_properties,
            compared_properties=compared_properties,
            stage_controls=stage_controls,
        )
    selected_files = dict(selected._files)
    selected_files["molecular-edit.json"] = files["intent/edit.json"]
    selected_files["edit-selection.json"] = canonical_json_bytes(
        {"edit_digest": edit_digest, "members": members, "baseline": baseline}
    )
    result = ConstructionSet._create(
        selected_files, json.loads(selected.json_bytes), selected.report_text
    )
    object.__setattr__(result, "_roots", (protected,))
    return result
