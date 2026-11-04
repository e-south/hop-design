"""Portable figure from an admitted coordinate snapshot, without molecular search."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.molecular.printing.teaching import teaching_print_files
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf, rendering_identity
from hop_design.export.construction.survey.display_projection import display_projection_files
from hop_design.export.construction.survey.figure import compose_figure, domain_csv
from hop_design.export.construction.survey.guide import parameter_guide
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.models.construction.surveys.selection import InterfaceSurveySelection
from hop_design.serialization import canonical_json_bytes

from ..packets.publication import SourceBoundConstructionPacket
from .selection import load_query

if TYPE_CHECKING:
    from .choices import InterfaceSurveyChoices


@dataclass(frozen=True, init=False, repr=False)
class InterfaceSurveyFigure(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.interface-survey-figure-packet/v1"


def survey_figure(
    pool: InterfaceSurveyChoices,
    *,
    query: str | Path | dict[str, Any] | None,
    selection: str | Path | dict[str, Any] | None,
    display_axes: tuple[str, ...] | None = None,
) -> InterfaceSurveyFigure:
    selected = None
    if selection is not None:
        source = load_source_mapping(selection) if isinstance(selection, str | Path) else selection
        selected = InterfaceSurveySelection.model_validate_json(canonical_json_bytes(source))
        if query is None:
            query = selected.query.model_dump(mode="json", by_alias=True)
    query = load_query(query).model_dump(mode="json", by_alias=True)
    if selected is not None:
        checked = pool.select(
            target=selected.address.target,
            step=selected.address.step,
            materialized_realization_id=selected.materialized_realization_id,
            query=query,
        )
        if checked != selected.model_dump(mode="json", by_alias=True):
            raise ValueError("Selection does not describe this exact snapshot and figure query.")
    choices = pool.query(query)
    teaching = None
    overview = None
    if selected is not None:
        from .atlas import inspect_interface_survey_atlas

        request_root, index_root = pool._roots
        for root in pool._roots:
            root.require_unchanged()
        atlas = inspect_interface_survey_atlas(
            request_root.path,
            index_root.path,
            selection=selected.model_dump(mode="json", by_alias=True),
        )
        teaching = (dict(atlas._files)["teaching.svg"], json.loads(atlas.json_bytes)["teaching"])
        overview = dict(atlas._files)["overview.svg"]
    files = figure_files(
        choices,
        pool.parameter_key_svg_bytes,
        pool.parameter_key(),
        None if selected is None else selected.model_dump(mode="json", by_alias=True),
        teaching=teaching,
        overview=overview,
        display_axes=display_axes,
    )
    summary = {
        "schema": "hop.interface-survey-figure/v1",
        "validation": choices["validation"],
        **{
            k: choices[k] for k in ("request_digest", "snapshot_digest", "query_digest", "coverage")
        },
        "selection": None if selected is None else selected.model_dump(mode="json", by_alias=True),
        "rendering": rendering_identity(),
        "enumeration_scope": choices["enumeration_scope"],
    }
    packet = InterfaceSurveyFigure._create(
        files,
        summary,
        "# Complete construction space\n\n"
        "Open figure.pdf or figure.svg. The teaching key defines each molecular coordinate; "
        "each plotted path records a complete preparation. It is not processing chronology. "
        "domains.csv retains every value, full method name and conditional support count. "
        "Unresolved values are not exclusions. The admitted snapshot is integrity-checked; "
        "aggregate molecular replay is a separate operation.\n\n"
        "An optional selection.json is the same exact selection used by survey atlas and "
        "survey retrieve. Figure export does not evaluate or relax a requirement.\n",
    )
    object.__setattr__(packet, "_roots", pool._roots)
    return packet


def figure_files(
    choices: dict[str, Any],
    key: bytes,
    key_definition: dict[str, Any],
    selected: dict[str, Any] | None,
    *,
    teaching: tuple[bytes, dict[str, Any]] | None = None,
    overview: bytes | None = None,
    display_axes: tuple[str, ...] | None = None,
) -> dict[str, bytes]:
    """Keep the teaching key, plot, complete figure and exact query in every choice export."""
    identity = None if selected is None else selected["materialized_realization_id"]
    plot = render_survey_plot(choices, selected_identity=identity, display_axes=display_axes)
    if teaching is not None and teaching[1]["materialized_realization_id"] != identity:
        raise ValueError("Teaching and plotted selection must describe the same preparation.")
    figure = compose_figure(
        overview if overview is not None else key if teaching is None else teaching[0],
        plot,
        choices,
        selected_identity=identity,
    )
    files = {
        **display_projection_files(plot),
        "figure.svg": figure,
        "figure.pdf": render_report_pdf((figure,), title="HOP complete construction space"),
        "plot.svg": plot,
        "parameter-key.svg": key,
        "parameter-key.json": canonical_json_bytes(key_definition),
        "choices.json": canonical_json_bytes(choices),
        "query.json": canonical_json_bytes(choices["query"]),
        "domains.csv": domain_csv(choices),
        "parameter-guide.md": parameter_guide(key_definition),
    }
    if selected is not None:
        files["selection.json"] = canonical_json_bytes(selected)
    if teaching is not None:
        files["teaching.svg"] = teaching[0]
        files["teaching.json"] = canonical_json_bytes(teaching[1])
        files.update(teaching_print_files(teaching[0]))
    if overview is not None:
        files["overview.svg"] = overview
    return files
