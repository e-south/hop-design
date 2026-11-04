"""Translate explicit scaffold intent; keep the ordinary family request authoritative."""

import json
import tempfile
from pathlib import Path

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.family.brief import ScaffoldComparisonBrief
from hop_design.serialization import canonical_json_bytes

from ..product_request import _load_request
from .prepare import PreparedConstructionFamily, prepare_construction_family


def author_construction_family(path: str | Path) -> PreparedConstructionFamily:
    """Author a family from a brief; only explicitly supplied permissions replace input values."""
    path = Path(path)
    mapping = load_source_mapping(path)
    brief = ScaffoldComparisonBrief.model_validate_json(json.dumps(mapping))
    base_path = Path(brief.base_request)
    if not base_path.is_absolute():
        base_path = path.parent / base_path
    base, original = _load_request(base_path)
    if brief.product != base.endpoint:
        raise ValueError(
            "Requested product differs from the base endpoint; choose a matching base request."
        )
    data = json.loads(original)
    for dimension, local in (
        ("loop_nt", "loop_lengths_nt"),
        ("loop_side_paired_bp", "annealing_arm_lengths_bp"),
    ):
        permission = getattr(brief.geometry_permissions, dimension)
        if permission is not None:
            data["foldback"]["geometry"][local] = list(permission)
    if "requirements" in brief.model_fields_set:
        data["whole_route_constraints"]["hairpin_scaffold"] = (
            None if brief.requirements is None else brief.requirements.model_dump(mode="json")
        )
    if brief.materials is not None:
        data["materialization"] = brief.materials.model_dump(mode="json", by_alias=True)
    family = {
        "schema": "hop.construction-family/v1",
        "base_request": data,
        "members": [m.model_dump(mode="json") for m in brief.vary],
        "shared_properties": list(brief.hold),
        "display_preferences": [p.model_dump(mode="json") for p in brief.display_preferences],
        "bounds": brief.bounds.model_dump(mode="json"),
    }
    with tempfile.TemporaryDirectory(prefix="hop-family-author-") as temporary:
        request = Path(temporary) / "family.json"
        request.write_bytes(canonical_json_bytes(family))
        prepared = prepare_construction_family(request)
    files = dict(prepared._files)
    # Store a portable authoring source with the original base. Input paths are not identities.
    files["base-request.json"] = original
    files["comparison.json"] = canonical_json_bytes(
        {**mapping, "base_request": "base-request.json"}
    )
    return PreparedConstructionFamily._create(
        files, json.loads(prepared.json_bytes), prepared.report_text
    )
