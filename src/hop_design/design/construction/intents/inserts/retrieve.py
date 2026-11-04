"""Publish verified insert memberships atomically with their public selection."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from hop_design.export.construction.handoff.insert_set import render_insert_set_report
from hop_design.export.construction.handoff.material_set import render_set_materials
from hop_design.serialization import canonical_json_bytes

from ...families.selection import ConstructionSet
from ...surveys.retrieve import retrieve_interface_survey_witness
from ..base import Source
from ..comparisons import source_value
from .admission import admitted_options
from .comparison import admit_set
from .handoff import comparison_handoff
from .selection import native_selection

if TYPE_CHECKING:
    from ..results import InsertDesignChoices


@dataclass(frozen=True)
class InsertSetHandoff:
    directory: Path
    materialized_realization_ids: tuple[str, ...]


def retrieve_preserved(
    choices: InsertDesignChoices, source: Source, destination: str | Path
) -> InsertSetHandoff:
    selected = source_value(source)
    native = native_selection(choices, selected)
    output = choices._output(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace selected preparation: {output}")
    with tempfile.TemporaryDirectory(prefix="hop-preserved-insert-") as temporary:
        root = Path(temporary) / "selected"
        receipt = retrieve_interface_survey_witness(
            choices._directory / "intent/request.json",
            choices._directory / "survey.sqlite",
            selection=native,
            destination=root,
        )
        files = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        packet = ConstructionSet._create(
            {**files, "design-selection.json": canonical_json_bytes(selected)},
            {
                "selection": selected,
                "materialized_realization_ids": list(receipt.materialized_realization_ids),
            },
            "# Selected insert\n\n[Exact preparation](preparation/report.md). "
            "[Preserved surroundings](design-selection.json) identify the molecular stage.\n",
        )
        object.__setattr__(packet, "_roots", ())
        choices._protect(packet).write(output)
    return InsertSetHandoff(output, receipt.materialized_realization_ids)


def retrieve_set(
    choices: InsertDesignChoices, source: Source, destination: str | Path
) -> InsertSetHandoff:
    value = source_value(source)
    selected = admit_set(choices, value)
    output = choices._output(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace selected comparison: {output}")
    identities: list[str] = []
    routes = {}
    with tempfile.TemporaryDirectory(prefix="hop-insert-set-") as temporary:
        root = Path(temporary)
        for name, member in sorted(selected.members.items()):
            native = native_selection(choices, member.model_dump(mode="json", by_alias=True))
            receipt = retrieve_interface_survey_witness(
                choices._directory / "intent/request.json",
                choices._directory / "survey.sqlite",
                selection=native,
                destination=root / "members" / name,
            )
            identities.extend(receipt.materialized_realization_ids)
            routes[name] = next(
                route
                for route in receipt._verified_source().result.realizations
                if route.materialized_realization_id == member.materialized_realization_id
            )
        summary = comparison_handoff(
            selected,
            routes,
            {option["label"]: option for option in admitted_options(choices)},
            choices.query(selected.query.model_dump(mode="json", by_alias=True)),
            {
                str(e.enzyme_id): e.canonical_name
                for e in choices._pool._request.enzyme_catalog.enzymes
            },
            root,
            choices._directory,
        )
        files = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        packet = ConstructionSet._create(
            {
                **files,
                **render_set_materials(tuple(routes.items())),
                "design-selection.json": canonical_json_bytes(selected),
                "comparison.json": canonical_json_bytes(summary),
            },
            {"selection": value, "materialized_realization_ids": identities, "comparison": summary},
            render_insert_set_report(summary),
        )
        object.__setattr__(packet, "_roots", ())
        choices._protect(packet).write(output)
    return InsertSetHandoff(output, tuple(identities))
