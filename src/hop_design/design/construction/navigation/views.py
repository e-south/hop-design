"""Restore inspection without revising requirements or starting discovery."""

import json
from pathlib import Path

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.variants.view import (
    AtlasExploration,
    AtlasPresentation,
    ColoredAtlasPresentation,
    ColoredAtlasViewReceipt,
    MolecularAtlasViewReceipt,
    ProjectedAtlasPresentation,
    ProjectedAtlasViewReceipt,
    ViewReceipt,
    parse_view_receipt,
)
from hop_design.models.construction.variants.view_color import AtlasColorLens
from hop_design.serialization import canonical_json_bytes

from ..intents.base import Source
from .guided_sampling import selection_source
from .landscape_source import has_molecular_landscape
from .landscape_source import landscape_digest as saved_landscape_digest
from .types import Camera, ChoiceSource, Record


def inspection_settings(
    *,
    presentation: Record | None = None,
    exploration: Record | None = None,
    choices: ChoiceSource | None = None,
) -> Record:
    """Validate presentation independently of selection or molecular identity."""
    settings = {
        "presentation": (
            ColoredAtlasPresentation
            if "color" in (presentation or {})
            else ProjectedAtlasPresentation
            if "display_axes" in (presentation or {})
            else AtlasPresentation
        )
        .model_validate_json(json.dumps(presentation or {}))
        .model_dump(mode="json"),
        "exploration": AtlasExploration.model_validate(exploration or {}).model_dump(mode="json"),
    }
    if choices is not None and "color" in settings["presentation"]:
        validate_color(choices, AtlasColorLens.model_validate(settings["presentation"]["color"]))
    return settings


def view_receipt(
    choices: ChoiceSource,
    selection: Source,
    *,
    stage: str = "all",
    reference_identity: str | None = None,
    camera: Camera = None,
    presentation: Record | None = None,
    exploration: Record | None = None,
    render_policy: str = "captured",
) -> Record:
    if (presentation or {}).get("landscape") == "similarity" and not has_molecular_landscape(
        choices
    ):
        raise ValueError("Create or capture molecular coordinates before saving a similarity view.")
    index = _view_membership(choices)
    landscape_digest = (
        saved_landscape_digest(choices, answer=index)
        if (presentation or {}).get("landscape") == "similarity"
        else None
    )
    raw = {
        "pool_digest": getattr(choices, "digest", None) or index["snapshot_digest"],
        "selection": selection_source(choices, selection),
        "stage": stage,
        "reference_identity": reference_identity,
        "camera": camera,
        "presentation": presentation or {},
        "exploration": exploration or {},
        "render_policy": render_policy,
        **(
            {"schema": "hop.atlas-view/v3", "landscape_digest": landscape_digest}
            if landscape_digest is not None
            else {}
        ),
    }
    if "display_axes" in (presentation or {}):
        raw["schema"] = "hop.atlas-view/v4"
    if "color" in (presentation or {}):
        raw["schema"] = "hop.atlas-view/v5"
    view = parse_view_receipt(json.loads(canonical_json_bytes(raw)))
    return _validated_view(choices, view, index, landscape_digest)


def restore_view(choices: ChoiceSource, source: Source) -> Record:
    raw = load_source_mapping(source) if isinstance(source, str | Path) else source
    view = parse_view_receipt(json.loads(canonical_json_bytes(raw)))
    index = _view_membership(choices)
    landscape_digest = (
        saved_landscape_digest(choices, answer=index)
        if view.presentation.landscape == "similarity" and has_molecular_landscape(choices)
        else None
    )
    return _validated_view(choices, view, index, landscape_digest)


def _view_membership(choices: ChoiceSource) -> Record:
    """Use admitted edition membership, without calculating unused facet counts.

    The selected route and coordinate file are still checked in this invocation.
    Live discoveries keep their existing query and snapshot-validation boundary.
    """
    from ..editions.reader import AtlasEdition

    if isinstance(choices, AtlasEdition):
        index = choices._selection_index
        return {
            "snapshot_digest": index.snapshot,
            "paths": [{"materialized_realization_id": identity} for identity in index.coordinates],
        }
    return choices.query()


def _validated_view(
    choices: ChoiceSource,
    view: ViewReceipt,
    index: Record,
    landscape_digest: str | None,
) -> Record:
    """Use evidence obtained in this invocation; retain nothing between calls."""
    if view.pool_digest != getattr(choices, "digest", index["snapshot_digest"]):
        raise ValueError("View belongs to a different recorded snapshot.")
    if isinstance(
        view, MolecularAtlasViewReceipt | ProjectedAtlasViewReceipt | ColoredAtlasViewReceipt
    ) and (view.landscape_digest != landscape_digest):
        raise ValueError("View coordinates differ from this edition's molecular landscape.")
    if isinstance(view, ColoredAtlasViewReceipt):
        validate_color(choices, view.presentation.color, index)
    identities = {p["materialized_realization_id"] for p in index["paths"]}
    if any(identity not in identities for identity in view.exploration.history):
        raise ValueError("Sampling history contains preparations outside this recorded pool.")
    states = choices._view_state_ids(view.selection)
    if view.reference_identity is not None:
        choices.select(view.reference_identity)
    if view.stage != "all" and view.stage not in states:
        raise ValueError("Viewed stage is not recorded in this preparation.")
    return view.model_dump(mode="json", by_alias=True)


def validate_color(
    choices: ChoiceSource, lens: AtlasColorLens, index: Record | None = None
) -> None:
    """Check admitted full-pool values; filtering does not redefine a color scale."""
    from ..editions.reader import AtlasEdition

    if lens.key == "none":
        return
    values = (
        (json.loads(raw) for rows in choices._selection_index.coordinates.values() for raw in rows)
        if isinstance(choices, AtlasEdition)
        else (path["values"] for path in (index if index is not None else choices.query())["paths"])
    )
    if not any(
        row.get(lens.key) is not None and (lens.word is None or row[lens.key] == lens.word)
        for row in values
    ):
        raise ValueError(
            "Color view is not applicable or has no matching word in this recorded pool."
        )
