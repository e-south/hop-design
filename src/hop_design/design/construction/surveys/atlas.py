"""On-demand exact molecular atlas for one indexed complete survey path."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.parameter_key import render_parameter_definition_key
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..packets.atlas import MolecularAtlasPacket
from ..packets.inspection import MolecularInspectionPacket
from ..projections.atlas import project_molecular_atlas
from ..projections.atlas_comparison import compare_route_atlases
from ..projections.parameter_locations import parameter_locations
from ..projections.parameter_teaching import parameter_teaching, survey_teaching_axes
from .admission import open_survey
from .choices import _project
from .execute import load_request
from .parameter_key import parameter_key
from .projection import witness_projection
from .selection import admit_selection
from .witness import recover_witness


@dataclass(frozen=True, init=False, repr=False)
class InterfaceSurveyAtlas(MolecularAtlasPacket):
    _packet_schema: ClassVar[str] = "hop.interface-survey-atlas-packet/v1"


def inspect_interface_survey_atlas(
    request_path: str | Path,
    index_path: str | Path,
    *,
    selection: str | Path | dict[str, Any],
    reference_selection: str | Path | dict[str, Any] | None = None,
) -> InterfaceSurveyAtlas:
    """Replay and draw the complete selected preparation without changing its query."""
    packet = _inspect_interface_survey_atlas(
        request_path,
        index_path,
        selection=selection,
        reference_selection=reference_selection,
        draw_route=True,
    )
    assert isinstance(packet, InterfaceSurveyAtlas)
    return packet


def _inspect_interface_survey_atlas(
    request_path: str | Path,
    index_path: str | Path,
    *,
    selection: str | Path | dict[str, Any],
    reference_selection: str | Path | dict[str, Any] | None = None,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    """Replay the selected witness, then project every recorded state and parameter.

    This reads the checkpoint without changing filters, permissions or search
    coverage. The exact identity guards against selecting a different trace.
    """
    roots = tuple(ProtectedRoot.capture(p) for p in (request_path, index_path))
    request = load_request(request_path)
    index, limits = open_survey(Path(index_path), request=request, producer=producer_identity())
    with index, tempfile.TemporaryDirectory(prefix="hop-survey-atlas-") as directory:
        selected = admit_selection(selection, request, index)
        reference = (
            None
            if reference_selection is None
            else admit_selection(reference_selection, request, index)
        )
        target, step = selected.address.target, selected.address.step
        materialized_realization_id = selected.materialized_realization_id
        receipt, product, record = recover_witness(
            index, request, limits, target=target, step=step, root=Path(directory)
        )
        if record["witnesses"] != [materialized_realization_id]:
            raise ValueError("Selected survey identity disagrees with the recorded witness.")
        projection = witness_projection(
            receipt, product.model_dump(mode="json"), materialized_realization_id
        )
        route = next(
            r
            for r in receipt._verified_source().result.realizations
            if r.materialized_realization_id == materialized_realization_id
        )
        comparison = None
        if reference is not None:
            recovered, _, reference_record = recover_witness(
                index,
                request,
                limits,
                target=reference.address.target,
                step=reference.address.step,
                root=Path(directory) / "reference",
            )
            if reference_record["witnesses"] != [reference.materialized_realization_id]:
                raise ValueError("Reference survey identity disagrees with its recorded witness.")
            old = next(
                r
                for r in recovered._verified_source().result.realizations
                if r.materialized_realization_id == reference.materialized_realization_id
            )
            comparison = compare_route_atlases(
                old,
                route,
                reference=reference.materialized_realization_id,
                option=selected.materialized_realization_id,
            )
        names = {str(e.enzyme_id): e.canonical_name for e in request.enzyme_catalog.enzymes}
        atlas = project_molecular_atlas(route, enzyme_names=names)
        locations = parameter_locations(route, atlas, projection["values"])
        choices = _project(
            request,
            [{"address": {"target": target, "step": step}, **projection}],
            index.coverage(),
            False,
            selected.query,
        )
        axes = survey_teaching_axes(choices["axes"])
        context = {
            **choices["context"],
            "coverage": choices["coverage"],
            "coverage_validation": choices["validation"],
            "evaluation_limits": limits.model_dump(mode="json"),
        }
        teaching = parameter_teaching(route, atlas, locations, projection["values"], axes, context)
        result: dict[str, object] = {
            "schema": "hop.interface-survey-atlas/v1",
            "validation": "selected_witness_replayed; aggregate_replay_separate",
            "request_digest": sha256_digest(canonical_json_bytes(request)),
            "address": {"target": target, "step": step},
            "selection": selected.model_dump(mode="json", by_alias=True),
            "reference_selection": None
            if reference is None
            else reference.model_dump(mode="json", by_alias=True),
            "comparison": None if comparison is None else comparison.model_dump(mode="json"),
            "projection": projection,
            "atlas": atlas.model_dump(mode="json"),
            "parameter_locations": locations,
            "teaching": teaching,
        }
        packet_type = InterfaceSurveyAtlas if draw_route else MolecularInspectionPacket
        packet = packet_type._create(
            {
                **(
                    {
                        "projection.svg": render_molecular_atlas(
                            atlas, comparison=comparison, parameter_locations=locations
                        ),
                        "teaching.svg": render_parameter_teaching(
                            teaching, atlas, locations, comparison=comparison
                        ),
                        "parameter-key.svg": render_parameter_definition_key(
                            parameter_key(request)
                        ),
                    }
                    if draw_route
                    else {}
                ),
                "request.json": canonical_json_bytes(request),
                "selection.json": canonical_json_bytes(selected),
                **(
                    {}
                    if reference is None
                    else {"reference-selection.json": canonical_json_bytes(reference)}
                ),
            },
            result,
            "# Complete survey construction\n\nOne exact replayed preparation, from source "
            "through released insert. Pairing is recorded architecture, not a conformation "
            "prediction. Primer inputs annotate recorded bindings; they do not introduce "
            "additional states. Inspection does not extend the search or select materials.\n\n"
            "[Parameter definitions](parameter-key.svg) describe the request without "
            "selected values. [Selected measurements](teaching.svg) locate this "
            "preparation. [All processing states](projection.svg) show its construction.\n",
        )
    object.__setattr__(packet, "_roots", roots)
    return packet
