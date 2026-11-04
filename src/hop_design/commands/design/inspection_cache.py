"""Owned, bounded preview files. Exported preparations have a separate lifetime."""

import json
import shutil
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from hop_design import construction
from hop_design.api import _InspectionProjection

from .inspection_view import processing_stage


def state_key(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class PreviewCache:
    def __init__(
        self, root: Path, *, entries: int = 4, byte_limit: int = 128 * 1024 * 1024
    ) -> None:
        self._temporary = TemporaryDirectory(prefix=".views-", dir=root)
        self.root = Path(self._temporary.name)
        self.entries, self.byte_limit = entries, byte_limit
        self._items: OrderedDict[str, tuple[dict[str, Any], int, Path]] = OrderedDict()
        self.bytes = 0

    def inspect(
        self,
        choices: construction.DesignChoices | construction.AtlasEdition,
        selection: dict[str, Any],
        reference: dict[str, Any] | None,
        settings: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        same = (settings.get("selection") or {}).get("materialized_realization_id") == selection[
            "materialized_realization_id"
        ]
        view = settings if same else {**settings, "stage": "all"}
        preview = self.get(choices, selection, reference, view=view)
        stage = processing_stage(preview, previous, settings["stage"])
        if stage != view["stage"] and settings["presentation"]["route"] == "assembly":
            preview = self.get(choices, selection, reference, view={**settings, "stage": stage})
        return preview, stage

    def get(
        self,
        choices: construction.DesignChoices | construction.AtlasEdition,
        selection: dict[str, Any],
        reference: dict[str, Any] | None = None,
        *,
        render_policy: str = "captured",
        view: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        settings = view or {}
        render_policy = settings.get("render_policy", render_policy)
        presentation = settings.get("presentation", {}).get("route", "complete")
        draw_route = settings.get("presentation", {}).get("molecule", "route") == "route"
        stage = settings.get("stage", "all") if presentation == "assembly" else "all"
        key = state_key(
            [
                selection,
                reference,
                render_policy,
                presentation,
                stage,
                draw_route,
                _InspectionProjection.profile,
            ]
        )
        if key not in self._items:
            inspect = choices.atlas if draw_route else choices._inspection_packet
            packet = inspect(
                selection,
                render_policy=render_policy,
                presentation=presentation,
                stage=stage,
                **({"reference_selection": reference} if reference else {}),
            )
            packet = _InspectionProjection.packet(packet)
            path = self.root / key
            try:
                packet.write(path, print_pages=False)
                size = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
                if size > self.byte_limit:
                    raise ValueError("This molecular preview exceeds the bounded preview cache.")
                summary = packet.inspection_summary(selection)
                relative = path.relative_to(self.root.parent).as_posix()
                value = {
                    "summary": summary,
                    "drawing": f"/files/{relative}/projection.svg" if draw_route else None,
                    "teaching": f"/files/{relative}/overview.svg",
                    "record": f"/files/{relative}/summary.json",
                    "teaching_geometry": _InspectionProjection.teaching(
                        (path / "overview.svg").read_bytes()
                    ),
                }
                self._items[key] = (value, size, path)
                self.bytes += size
            except BaseException:
                shutil.rmtree(path, ignore_errors=True)
                raise
        self._items.move_to_end(key)
        while len(self._items) > self.entries or self.bytes > self.byte_limit:
            _, (_, size, path) = self._items.popitem(last=False)
            self.bytes -= size
            shutil.rmtree(path)
        return self._items[key][0]

    def close(self) -> None:
        self._items.clear()
        self.bytes = 0
        self._temporary.cleanup()
