"""Read-only exact hairpin previews, without drawing the complete processing route."""

import json
import tempfile
from pathlib import Path

from pydantic import ValidationError

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.molecular.teaching_overview import (
    render_projected_teaching,
    render_teaching_overview,
)
from hop_design.export.construction.presentation.figure_profile import (
    PUBLICATION_FIGURE,
    FigureProfile,
)
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.publication import ProtectedRoot

from ..packets.publication import SourceBoundConstructionPacket
from ..projections.atlas import project_molecular_atlas
from ..projections.parameter_locations import parameter_locations
from ..projections.parameter_teaching import parameter_teaching, survey_teaching_axes
from .types import ChoiceSource, Record


class MolecularPreview(SourceBoundConstructionPacket):
    _packet_schema = "hop.molecular-preview/v1"


def _current_record(choices: ChoiceSource, path: Record, answer: Record) -> Record:
    from ..intents.hairpin_choices import HairpinDesignChoices
    from ..intents.results import InsertDesignChoices
    from ..surveys.admission import open_survey
    from ..surveys.selection import admit_selection
    from ..surveys.witness import recover_witness

    identity = path["materialized_realization_id"]
    if isinstance(choices, HairpinDesignChoices):
        route = next(
            r for _, r in choices._pool._routes if r.materialized_realization_id == identity
        )
    elif isinstance(choices, InsertDesignChoices):
        pool = choices._pool
        index, limits = open_survey(
            choices._directory / "survey.sqlite",
            request=pool._request,
            producer=producer_identity(),
        )
        with index, tempfile.TemporaryDirectory(prefix="hop-preview-") as directory:
            selected = admit_selection(choices.select(identity), pool._request, index)
            receipt, _, record = recover_witness(
                index,
                pool._request,
                limits,
                target=selected.address.target,
                step=selected.address.step,
                root=Path(directory),
            )
            if record["witnesses"] != [identity]:
                raise ValueError("Preview identity disagrees with the recorded witness.")
            route = next(
                r
                for r in receipt._verified_source().result.realizations
                if r.materialized_realization_id == identity
            )
    else:
        raise TypeError("This choice source has no admitted hairpin preview.")
    names = {
        node["value"]: node["label"]
        for axis in answer["axes"]
        if axis["key"].endswith("method")
        for node in axis["nodes"]
    }
    atlas = project_molecular_atlas(route, enzyme_names=names)
    locations = parameter_locations(route, atlas, path["values"])
    teaching = parameter_teaching(
        route, atlas, locations, path["values"], survey_teaching_axes(answer["axes"]), {}
    )
    return {
        "atlas": atlas.model_dump(mode="json"),
        "teaching": teaching,
        "parameter_locations": locations,
    }


def preview_record(choices: ChoiceSource, identity: str, answer: Record) -> tuple[Record, bool]:
    """Admit one molecular record; drawing choices do not alter its identity."""
    from ..editions.reader import AtlasEdition

    path = next((p for p in answer["paths"] if p["materialized_realization_id"] == identity), None)
    if path is None:
        raise ValueError("Preview must name a preparation in the recorded pool.")
    if not isinstance(choices, AtlasEdition):
        return _current_record(choices, path, answer), False
    if choices._store.compact:
        from ..editions.compact_projection import compact_molecule

        return compact_molecule(choices, identity, answer), False
    if answer["snapshot_digest"] != choices._store.manifest.snapshot_digest:
        raise ValueError("Preview context disagrees with the edition snapshot.")
    summary = json.loads(choices._store.read(choices._prefix(identity) + "/atlas/summary.json"))
    if summary["atlas"]["materialized_realization_id"] != identity:
        raise ValueError("Captured preview disagrees with the preparation identity.")
    return summary, True


def preview_components(
    choices: ChoiceSource,
    identity: str,
    answer: Record,
    *,
    profile: FigureProfile = PUBLICATION_FIGURE,
    render_policy: str = "captured",
) -> tuple[bytes, Record]:
    """Acquire the verified glyph once; publication and inspection compose it separately."""
    from ..editions.reader import AtlasEdition

    if render_policy not in {"captured", "current"}:
        raise ValueError("Choose captured or current render policy.")
    path = next((p for p in answer["paths"] if p["materialized_realization_id"] == identity), None)
    if path is None:
        raise ValueError("Preview must name a preparation in the recorded pool.")
    rendering = "current"
    if isinstance(choices, AtlasEdition) and choices._store.compact:
        from ..editions.compact_projection import compact_teaching_projection

        atlas, summary = compact_teaching_projection(choices, identity, answer)
        overview = render_projected_teaching(
            atlas, summary["teaching"], summary["parameter_locations"], profile=profile
        )
        cost = atlas.construction_cost.model_dump(mode="json") if atlas.construction_cost else None
    else:
        summary, captured = preview_record(choices, identity, answer)
        if captured:
            assert isinstance(choices, AtlasEdition)
            overview = choices._store.read(choices._prefix(identity) + "/atlas/overview.svg")
            rendering = "captured"
            if render_policy == "current":
                try:
                    overview = render_teaching_overview(summary, profile=profile)
                except ValidationError:
                    pass  # Unsupported future records retain their checked artwork.
                else:
                    rendering = "current"
        else:
            overview = render_teaching_overview(summary, profile=profile)
        cost = summary["atlas"].get("construction_cost")
    return overview, {
        "materialized_realization_id": identity,
        "snapshot_digest": answer["snapshot_digest"],
        "eligible": path["matches"],
        "path": path,
        "rendering": rendering,
        "construction_cost": cost,
    }


def preview_preparation(
    choices: ChoiceSource, identity: str, *, query: str | Path | Record | None = None
) -> MolecularPreview:
    answer = choices.query(query)
    overview, summary = preview_components(choices, identity, answer)
    packet = MolecularPreview._create(
        {
            "overview.svg": overview,
            "trace.svg": render_survey_plot(answer, selected_identity=identity),
        },
        summary,
        "# Molecular preview\n\nOne recorded hairpin and its exact parameter trace. "
        "Inspection does not select a preparation or alter the query.\n",
    )
    object.__setattr__(packet, "_roots", (ProtectedRoot.capture(choices._directory),))
    return packet
