"""Bounded transient hairpin drawings, separate from committed route inspection."""

import copy
import shutil
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from typing import TYPE_CHECKING, Any

from hop_design import construction
from hop_design.api import _InspectionProjection

from .inspection_cache import state_key
from .inspection_worker import SingleWorker

if TYPE_CHECKING:
    from .inspection import DesignInspectionSession


def neighboring_preparations(
    session: "DesignInspectionSession", payload: dict[str, Any]
) -> dict[str, Any]:
    """A deliberate inspector request; verification is never part of pointer movement."""
    with session._lock:
        session._check(payload, optional={"verify_controls", "request_id"})
        request_id = payload.get("request_id")
        if request_id is not None and (
            not isinstance(request_id, str) or not 1 <= len(request_id) <= 64
        ):
            raise ValueError(
                "Neighbor request identity must be a nonempty string of at most 64 characters."
            )
        selected = session._state["selection"]
        if selected is None:
            raise ValueError("Pin an eligible preparation before inspecting its neighbors.")
        session._neighbor_cancel.set()
        if not session._neighbor_lock.acquire(blocking=False):
            raise ValueError("The previous neighbor inspection is stopping; retry shortly.")
        session._neighbor_cancel = Event()
        session._neighbor_done.clear()
        session._neighbor_request = request_id
        work = _InspectionProjection.neighbor_work(cancelled=session._neighbor_cancel)
        identity = selected["materialized_realization_id"]
        query = copy.deepcopy(session._state["choices"]["query"])
        answer = session._state["choices"]
    try:
        result = _InspectionProjection.neighbors(
            session.designs,
            identity,
            query=query,
            verify_controls=payload.get("verify_controls", True),
            work=work,
            answer=answer,
        )
        with session._lock:
            work.check()
            session._check(payload, optional={"verify_controls", "request_id"})
        return result
    finally:
        session._neighbor_done.set()
        session._neighbor_lock.release()


def cancel_neighbors(session: "DesignInspectionSession", payload: dict[str, Any]) -> dict[str, str]:
    with session._lock:
        session._check(payload, {"request_id"})
        if payload["request_id"] != session._neighbor_request:
            return {"status": "superseded"}
        session._neighbor_cancel.set()
    return {"status": "cancelled"}


class HoverCache:
    def __init__(self, root: Path, *, entries: int = 12, byte_limit: int = 8 * 1024 * 1024):
        self._temporary = TemporaryDirectory(prefix=".hover-", dir=root)
        self.root = Path(self._temporary.name)
        self.entries, self.byte_limit, self.bytes = entries, byte_limit, 0
        self._items: OrderedDict[str, tuple[dict[str, Any], Path, int, bool]] = OrderedDict()
        self._worker = SingleWorker(_InspectionProjection.render_preview_job)

    def get(
        self,
        choices: construction.DesignChoices | construction.AtlasEdition,
        identity: str,
        query: dict[str, Any],
        *,
        answer: dict[str, Any] | None = None,
        render_policy: str = "captured",
        phases: tuple[str, ...] | None = None,
        presentation: str = "complete",
    ) -> dict[str, Any]:
        key = state_key(
            [identity, query, _InspectionProjection.profile, render_policy, phases, presentation]
        )

        def build(path: Path) -> dict[str, Any]:
            context = choices.query(query) if answer is None else answer
            job = _InspectionProjection.preview_job(
                choices,
                identity,
                context,
                render_policy=render_policy,
                phases=phases,
                presentation=presentation,
            )
            overview, summary = (
                self._worker.call(job)
                if job is not None
                else _InspectionProjection.preview(
                    choices, identity, context, render_policy=render_policy
                )
            )
            if phases is not None:
                if job is not None:
                    drawings, metadata = summary.pop("route_drawings"), summary["route_scenes"]
                else:
                    drawings, metadata = _InspectionProjection.scenes(
                        choices,
                        identity,
                        context,
                        phases=phases,
                        presentation=presentation,
                        render_policy=render_policy,
                    )
                    summary["route_scenes"] = metadata
                self._write_scenes(path, drawings, metadata)
            (path / "overview.svg").write_bytes(overview)
            return {
                **summary,
                "molecule": self._url(path / "overview.svg"),
                "teaching_geometry": _InspectionProjection.teaching(overview),
            }

        return self._retain(key, build)

    def scenes(
        self,
        choices: construction.DesignChoices | construction.AtlasEdition,
        identity: str,
        answer: dict[str, Any],
        phases: tuple[str, ...],
        *,
        presentation: str,
        render_policy: str,
    ) -> dict[str, Any]:
        key = state_key(
            [
                "scenes",
                identity,
                answer["snapshot_digest"],
                phases,
                presentation,
                render_policy,
                _InspectionProjection.profile,
            ]
        )

        def build(path: Path) -> dict[str, Any]:
            drawings, result = _InspectionProjection.scenes(
                choices,
                identity,
                answer,
                phases=phases,
                presentation=presentation,
                render_policy=render_policy,
            )
            self._write_scenes(path, drawings, result)
            return result

        return self._retain(key, build, scenes=True)

    def _write_scenes(
        self, path: Path, drawings: dict[str, bytes], metadata: dict[str, Any]
    ) -> None:
        for index, scene in enumerate(metadata["scenes"]):
            target = path / f"scene-{index}.svg"
            target.write_bytes(drawings[scene["state_id"]])
            scene["drawing"] = self._url(target)

    def _url(self, path: Path) -> str:
        return "/files/" + path.relative_to(self.root.parent).as_posix()

    def _retain(
        self, key: str, build: Callable[[Path], dict[str, Any]], *, scenes: bool = False
    ) -> dict[str, Any]:
        if key not in self._items:
            path = self.root / key
            try:
                path.mkdir()
                value = build(path)
                size = sum(p.stat().st_size for p in path.iterdir() if p.is_file())
                if size > self.byte_limit:
                    raise ValueError("Molecular preview exceeds the bounded hover cache.")
                self._items[key] = value, path, size, scenes
                self.bytes += size
            except BaseException:
                shutil.rmtree(path, ignore_errors=True)
                raise
        self._items.move_to_end(key)
        # Route scenes and teaching previews have separate entry quotas, but
        # share the unchanged byte ceiling. A visible route must not flush an
        # otherwise small teaching working set on each hover.
        while True:
            same_kind = [k for k, item in self._items.items() if item[3] == scenes]
            if len(same_kind) > self.entries:
                evicted = same_kind[0]
            elif self.bytes > self.byte_limit:
                evicted = next(iter(self._items))
            else:
                break
            _, path, size, _ = self._items.pop(evicted)
            self.bytes -= size
            shutil.rmtree(path)
        return copy.deepcopy(self._items[key][0])

    def stop(self) -> None:
        """Interrupt process work before the session waits for its state lock."""
        self._worker.close()

    def close(self) -> None:
        self.stop()
        self._items.clear()
        self.bytes = 0
        self._temporary.cleanup()
