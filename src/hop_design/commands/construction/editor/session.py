"""One local editor's transient interaction state, composed from public HOP operations."""

import copy
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from hop_design import construction


class EditorSession:
    def __init__(self, request: Path, output: Path):
        initial = construction.prepare_scaffold_discovery(request)
        output.mkdir(parents=True, exist_ok=False)
        self.root = output.resolve()
        initial.write(self.root / "original")
        self.original = self.root / "original/request.json"
        self.request = json.loads(self.original.read_bytes())
        self._lock = threading.RLock()
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hop-editor")
        self._intent: Path | None = None
        self._evaluated: Path | None = None
        self._revision = 0
        self._selection_count = 0
        self._state: dict[str, Any] = {
            "original_request": self.request,
            "preview": None,
            "result": None,
            "selection": None,
            "busy": False,
            "error": None,
            "timings": {},
        }

    def state(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def _idle(self) -> None:
        if self._state["busy"]:
            raise ValueError("An explicit evaluation is already running; wait for its result.")

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "loop_sequences",
            "end_placements",
            "end_words",
            "basal_nick_enzyme_ids",
            "release_enzyme_ids",
        }
        if not payload or set(payload) - allowed:
            raise ValueError(
                "Preview accepts exact loop words and explicit released-end edits only."
            )
        arguments: dict[str, Any] = {}
        for key, value in payload.items():
            if key == "end_placements":
                if not isinstance(value, list) or not all(
                    isinstance(p, list) and len(p) == 2 and all(type(n) is int for n in p)
                    for p in value
                ):
                    raise ValueError(
                        "End placements must be an array of integer [left, right] pairs."
                    )
                arguments[key] = tuple(tuple(p) for p in value)
            else:
                if not isinstance(value, list) or not all(isinstance(w, str) for w in value):
                    raise ValueError(f"{key} must be an array of exact strings.")
                if key == "end_words" and len(value) != 2:
                    raise ValueError("Specify exactly two end words.")
                arguments[key] = tuple(value)
        with self._lock:
            self._idle()
            start = time.perf_counter()
            packet = construction.author_molecular_edit(self.original, **arguments)
            self._revision += 1
            self._intent = packet.write(self.root / "intents" / f"{self._revision:04d}")
            self._state["preview"] = json.loads(packet.json_bytes)
            self._state["selection"] = None
            self._state["error"] = None
            self._state["timings"]["preview_seconds"] = time.perf_counter() - start
            return self.state()

    def _current(self, digest: Any) -> None:
        preview = self._state["preview"]
        if preview is None or digest != preview["edit_digest"]:
            raise ValueError("Stale edit: preview the current request before continuing.")

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"edit_digest"}:
            raise ValueError("Evaluation requires exactly one edit_digest.")
        with self._lock:
            self._idle()
            self._current(payload["edit_digest"])
            if self._state["preview"]["status"] != "ready":
                raise ValueError("Resolve the preview conflicts before evaluation.")
            assert self._intent is not None
            destination = self.root / "evaluations" / f"{self._revision:04d}"
            if destination.exists():
                raise ValueError(
                    "This revision is already evaluated; use its results or make a new preview."
                )
            self._state.update(busy=True, error=None, selection=None)
            self._worker.submit(self._evaluate, self._intent / "edit.json", destination)
            return self.state()

    def _evaluate(self, path: Path, destination: Path) -> None:
        start = time.perf_counter()
        try:
            packet = construction.execute_molecular_edit(path)
            packet.write(destination)
            result = json.loads(packet.json_bytes)
            for option in result["options"]:
                view = json.loads((destination / option["sequence_view"]).read_bytes())
                option["loop_sequence"] = next(
                    r["observed_sequence"] for r in view["regions"] if r["region"] == "loop"
                )
                option["changed_material_roles"] = view["changed_material_roles"]
            result["files_prefix"] = "/files/" + destination.relative_to(self.root).as_posix() + "/"
            with self._lock:
                self._evaluated = destination
                self._state["result"] = result
        except Exception as error:
            # The HTTP caller cannot observe a worker Future's exception. Preserve
            # its failure explicitly instead of leaving a silent, empty result.
            with self._lock:
                self._state["error"] = f"{type(error).__name__}: {error}"
        finally:
            with self._lock:
                self._state["busy"] = False
                self._state["timings"]["evaluation_seconds"] = time.perf_counter() - start

    def select(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"edit_digest", "members", "baseline", "shared_properties"}:
            raise ValueError(
                "Selection requires edit_digest, members, baseline and shared_properties."
            )
        members, baseline, shared = (
            payload["members"],
            payload["baseline"],
            payload["shared_properties"],
        )
        if (
            not isinstance(members, dict)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in members.items())
            or not isinstance(baseline, str)
            or not isinstance(shared, list)
            or not all(isinstance(v, str) for v in shared)
        ):
            raise ValueError("Invalid explicit molecular selection.")
        with self._lock:
            self._idle()
            self._current(payload["edit_digest"])
            result = self._state["result"]
            if (
                self._evaluated is None
                or result is None
                or result["edit_digest"] != payload["edit_digest"]
            ):
                raise ValueError("Stale results: evaluate this edit before selecting.")
            start = time.perf_counter()
            packet = construction.select_molecular_edit(
                self._evaluated,
                edit_digest=payload["edit_digest"],
                members=members,
                baseline=baseline,
                shared_properties=tuple(shared),
            )
            self._selection_count += 1
            destination = self.root / "selections" / f"{self._selection_count:04d}"
            packet.write(destination)
            archive = destination.with_suffix(".zip")
            with ZipFile(archive, "x", compression=ZIP_DEFLATED) as zipped:
                for file in sorted(destination.rglob("*")):
                    if file.is_file():
                        info = ZipInfo(
                            file.relative_to(destination).as_posix(), (1980, 1, 1, 0, 0, 0)
                        )
                        info.compress_type = ZIP_DEFLATED
                        zipped.writestr(info, file.read_bytes())
            self._state["selection"] = {
                "archive": "/files/" + archive.relative_to(self.root).as_posix(),
                "report": "/files/" + destination.relative_to(self.root).as_posix() + "/report.md",
                "members": list(members),
                "edit_digest": payload["edit_digest"],
            }
            self._state["timings"]["retrieval_seconds"] = time.perf_counter() - start
            return self.state()

    def close(self) -> None:
        self._worker.shutdown(wait=True, cancel_futures=True)
