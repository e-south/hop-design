"""One bounded discovery invocation, independent of the pinned inspection snapshot."""

import copy
import json
import multiprocessing
import re
import shlex
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any

from hop_design import construction

from .inspection_discovery_worker import execute_discovery

type Worker = Callable[[Connection, Any, Path, dict[str, Any] | None, int, int | None], None]
_ACTIVE = {"running", "stopping"}


def default_request(resolution: dict[str, Any]) -> dict[str, Any] | None:
    """Keep exact intent and permissions portable; do not reinterpret families."""
    if resolution.get("schema") != "hop.resolved-design-request/v1":
        return None
    intent = {
        key: value for key, value in resolution["intent"].items() if key != "prefer_preparation"
    }
    # This optional search-order reference belongs to the original intent packet.
    # A fresh branch keeps molecular permissions without borrowing its local paths.
    return copy.deepcopy({**intent, "context": resolution["permissions"]})


class DiscoveryWork:
    def __init__(self, root: Path, *, worker: Worker = execute_discovery) -> None:
        self._root, self._worker = root, worker
        self._lock = threading.RLock()
        self._process: BaseProcess | None = None
        self._monitor: threading.Thread | None = None
        self._stopped: Any = None
        self._job: dict[str, Any] | None = None
        self._closed = False
        self._inspecting = False

    @property
    def output_directory(self) -> Path:
        return self._root

    def snapshot(self, job_id: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            if job_id is not None:
                self._check_id(job_id)
            return copy.deepcopy(self._job)

    def _check_id(self, job_id: str) -> None:
        if self._closed:
            raise ValueError("The discovery inspector is closed.")
        if self._job is None or job_id != self._job["id"]:
            raise ValueError("This discovery invocation is absent or superseded.")

    def _available(self) -> None:
        if self._closed:
            raise ValueError("The discovery inspector is closed.")
        if self._inspecting:
            raise ValueError("The saved discovery is being opened; wait before continuing it.")
        if self._job is not None and self._job["status"] in _ACTIVE:
            raise ValueError("A discovery is already running; stop or finish it first.")

    @contextmanager
    def inspectable_result(self, job_id: str) -> Iterator[Path]:
        """Reserve one committed snapshot while admission runs outside session locks."""
        with self._lock:
            self._check_id(job_id)
            self._available()
            assert self._job is not None
            count = self._job.get("matching_preparations")
            if self._job["status"] not in {"completed", "cancelled"} or not count:
                raise ValueError("No complete preparations are available to inspect yet.")
            directory = Path(self._job["directory"])
            self._inspecting = True
        try:
            yield directory
        finally:
            with self._lock:
                self._inspecting = False

    def begin(
        self,
        request: dict[str, Any] | None,
        *,
        evaluations: int = 64,
        first_choices: int | None = None,
        previous: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._available()
        if type(evaluations) is not int or evaluations < 1:
            raise ValueError("Evaluations must be a positive integer.")
        if first_choices is not None and (type(first_choices) is not int or first_choices < 1):
            raise ValueError("First choices must be a positive integer.")
        if previous is None:
            stem = request.get("stem_arm") if isinstance(request, dict) else None
            if not isinstance(stem, str) or not re.fullmatch("[ACGT]+", stem):
                raise ValueError(
                    "Browser discovery requires one exact stem; "
                    "family and staged revision feedback are not supported."
                )
            assert request is not None
            request = copy.deepcopy(request)
            resolved = construction.resolve_design_request(request)
            if json.loads(resolved.json_bytes).get("schema") != "hop.resolved-design-request/v1":
                raise ValueError("Browser discovery requires an exact-stem request.")
            # Validation may rewrite references into packet-relative paths. The
            # worker must resolve the authored mapping, from the same launch cwd,
            # so explicit context and preferred-preparation paths remain valid.
        elif request is not None:
            raise ValueError("Continue the saved request without replacing its permissions.")
        with self._lock:
            self._available()
            if previous is not None:
                self._check_id(previous)
                assert self._job is not None
                if not self._job["can_continue"]:
                    raise ValueError("This result cannot be continued unchanged.")
                directory = Path(self._job["directory"])
            else:
                directory = self._root / "discoveries" / uuid.uuid4().hex
            if self._process is not None:
                self._process.close()
                self._process = None
            context = multiprocessing.get_context("spawn")
            reader, writer = context.Pipe(duplex=False)
            stopped = context.Event()
            process = context.Process(
                target=self._worker,
                args=(writer, stopped, directory, request, evaluations, first_choices),
            )
            job = {
                "id": uuid.uuid4().hex,
                "directory": str(directory),
                "status": "running",
                "progress": None,
                "can_continue": False,
                "message": None,
                "matching_preparations": None,
                "command": None,
            }
            try:
                process.start()
            except BaseException:
                reader.close()
                writer.close()
                process.close()
                raise
            writer.close()
            self._job, self._process, self._stopped = job, process, stopped
            self._monitor = threading.Thread(
                target=self._collect,
                args=(job["id"], reader, process),
                daemon=True,
                name="hop-discovery-progress",
            )
            self._monitor.start()
            return copy.deepcopy(job)

    def _collect(self, job_id: str, reader: Connection, process: BaseProcess) -> None:
        result: dict[str, Any] | None = None
        try:
            while True:
                message = reader.recv()
                if message["kind"] == "finished":
                    result = message
                    break
                with self._lock:
                    if self._job is not None and self._job["id"] == job_id:
                        self._job["progress"] = message["progress"]
        except (EOFError, OSError):
            pass
        finally:
            reader.close()
            process.join()
            with self._lock:
                if self._job is not None and self._job["id"] == job_id:
                    value = result or {
                        "status": "interrupted" if self._closed else "failed",
                        "message": "Discovery stopped without a final result; "
                        "committed files remain available.",
                        "resumable": False,
                    }
                    self._job.update(
                        status=value["status"],
                        message=value.get("message"),
                        can_continue=value["resumable"],
                        matching_preparations=value.get("matching_preparations"),
                    )
                    if result is not None and value["status"] in {"completed", "cancelled"}:
                        directory = self._job["directory"]
                        self._job["command"] = shlex.join(
                            ["hop-design", "design", "continue", directory, "--evaluations", "64"]
                            if value.get("matching_preparations") is None
                            else [
                                "hop-design",
                                "design",
                                "view",
                                directory,
                                "--out",
                                str(Path(directory).with_name(Path(directory).name + "-view")),
                            ]
                        )

    def stop(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            self._check_id(job_id)
            assert self._job is not None
            if self._job["status"] in _ACTIVE:
                self._stopped.set()
                self._job["status"] = "stopping"
            return copy.deepcopy(self._job)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            process, monitor = self._process, self._monitor
            if self._stopped is not None:
                self._stopped.set()
        if process is not None:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            if monitor is not None:
                monitor.join(timeout=1)
            process.close()
            with self._lock:
                self._process = None
