"""Bounded cohort drawings; inspecting a preparation does not invalidate the landscape."""

import json
import shutil
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from hop_design import construction
from hop_design.api import _InspectionProjection

from .inspection_cache import state_key
from .inspection_transport import compact_choices


class InspectionPlots:
    def __init__(self, root: Path, *, entries: int = 4, byte_limit: int = 16 * 1024 * 1024):
        self._temporary = TemporaryDirectory(prefix=".plots-", dir=root)
        self.root = Path(self._temporary.name)
        self.entries, self.byte_limit, self.bytes = entries, byte_limit, 0
        self._items: OrderedDict[str, tuple[dict[str, Any], Path, int]] = OrderedDict()
        self._projection_key: str | None = None
        self._projection: _InspectionProjection.Trace | None = None

    def projection(
        self, answer: dict[str, Any], display_axes: tuple[str, ...] | None = None
    ) -> _InspectionProjection.Trace:
        key = state_key(
            [
                answer["snapshot_digest"],
                answer["query_digest"],
                display_axes,
                _InspectionProjection.profile,
            ]
        )
        if self._projection_key != key:
            self._projection = _InspectionProjection.trace(answer, display_axes=display_axes)
            self._projection_key = key
        assert self._projection is not None
        return self._projection

    def get(
        self,
        choices: construction.DesignChoices | construction.AtlasEdition,
        state: dict[str, Any],
        *,
        compact: bool = False,
    ) -> dict[str, Any]:
        query, stage = state["choices"]["query"], state["family_stage"]
        layout = state["presentation"]["layout"]
        active = state["presentation"]["landscape"]
        display_axes = state["presentation"].get("display_axes")
        drawing = {"display_axes": tuple(display_axes)} if display_axes is not None else {}
        key = state_key(
            [
                state["choices"].get("snapshot_digest"),
                query,
                stage,
                layout,
                active,
                compact,
                display_axes,
                _InspectionProjection.profile,
            ]
        )
        if key not in self._items:
            path = self.root / key
            try:
                path.mkdir()
                urls = {}
                families = (
                    _InspectionProjection.families(
                        state["choices"],
                        stage=stage,
                        endpoint=choices.resolution["intent"]["product"],
                    )
                    if compact
                    else choices.families(query=query, stage=stage)
                )
                # The active map and its linked parameter trace are visible.
                # Other layouts are generated only when the presentation changes.
                modes = dict.fromkeys(("parameters",) if compact else ("parameters", active))
                for mode in modes:
                    options = {"stage": stage, "layout": layout} if mode == "families" else {}
                    svg = (
                        _InspectionProjection.axes(state["choices"], **drawing)
                        if compact
                        else choices.plot_svg_bytes(
                            query, selected_identity=None, view=mode, **options
                        )
                    )
                    target = path / (mode + ".svg")
                    target.write_bytes(svg)
                    urls[mode] = "/files/" + target.relative_to(self.root.parent).as_posix()
                if compact:
                    urls["inspection"] = urls["parameters"]
                else:
                    target = path / "inspection.svg"
                    target.write_bytes(_InspectionProjection.axes(state["choices"], **drawing))
                    urls["inspection"] = "/files/" + target.relative_to(self.root.parent).as_posix()
                target = path / "distributions.svg"
                target.write_bytes(
                    _InspectionProjection.distributions(families["distributions"])
                    if compact
                    else choices.plot_svg_bytes(
                        query, selected_identity=None, view="distributions", stage=stage
                    )
                )
                urls["distributions"] = "/files/" + target.relative_to(self.root.parent).as_posix()
                value = {
                    "plots": urls,
                    "has_landscape": choices.has_landscape,
                    "families": families,
                    "explanation": choices.explain(query),
                }
                if compact:
                    value.update(
                        compact=compact_choices(_InspectionProjection.display(state["choices"])),
                        map_index=_InspectionProjection.map(choices, state["choices"]),
                        cohort_summary={
                            "product": families["product"],
                            "products": len(families["products"]),
                            "eligible_products": sum(
                                bool(p["eligible_preparations"]) for p in families["products"]
                            ),
                        },
                        families=None,
                    )
                    (path / "cohort.json").write_text(
                        json.dumps(
                            {k: value[k] for k in ("compact", "map_index", "cohort_summary")},
                            separators=(",", ":"),
                        )
                    )
                size = sum(p.stat().st_size for p in path.iterdir())
                if size > self.byte_limit:
                    raise ValueError("Choice drawings exceed the bounded inspection cache.")
                self._items[key] = value, path, size
                self.bytes += size
            except BaseException:
                shutil.rmtree(path, ignore_errors=True)
                raise
        self._items.move_to_end(key)
        while len(self._items) > self.entries or self.bytes > self.byte_limit:
            _, (_, path, size) = self._items.popitem(last=False)
            self.bytes -= size
            shutil.rmtree(path)
        return self._items[key][0]

    def close(self) -> None:
        self._projection = None
        self._projection_key = None
        self._items.clear()
        self.bytes = 0
        self._temporary.cleanup()
