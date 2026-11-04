"""Loopback-only HTTP adapter with origin, host and per-instance request protection."""

from __future__ import annotations

import errno
import json
import mimetypes
import secrets
import socket
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urlsplit

from hop_design import construction

if TYPE_CHECKING:
    from ...design.inspection import DesignInspectionSession
from .assets import asset_response
from .session import EditorSession
from .surveys import SurveySession
from .variants import VariantSession


def send_response_body(connection: socket.socket, body: bytes) -> None:
    """Bound writes and retry transient buffer pressure without replaying sent bytes."""
    original_timeout = connection.gettimeout()
    deadline = time.monotonic() + (original_timeout if original_timeout is not None else 15)
    delay = 0.01
    remaining = memoryview(body)
    try:
        while remaining:
            budget = deadline - time.monotonic()
            if budget <= 0:
                raise TimeoutError("Local response exceeded its transfer deadline.")
            connection.settimeout(budget)
            try:
                sent = connection.send(remaining[: 64 * 1024])
            except OSError as error:
                if error.errno != errno.ENOBUFS:
                    raise
                time.sleep(min(delay, budget))
                delay = min(0.1, delay * 2)
                continue
            if sent == 0:
                raise ConnectionError("Local response connection closed during transfer.")
            remaining = remaining[sent:]
            delay = 0.01
    finally:
        remaining.release()
        connection.settimeout(original_timeout)


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        session: EditorSession | VariantSession | SurveySession | DesignInspectionSession,
        port: int,
    ):
        self.session = session
        self._inspection_transition = threading.Lock()
        self._closing = False
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), EditorHandler)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"

    def server_close(self) -> None:
        with self._inspection_transition:
            self._closing = True
        super().server_close()


class EditorHandler(BaseHTTPRequestHandler):
    server: EditorServer

    def log_message(self, format: str, *args: object) -> None:
        # Do not put request bodies, paths or transient authorization values in a console log.
        return

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(15)

    def _respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; "
            "style-src 'self'; img-src 'self'; connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        send_response_body(self.connection, body)

    def _json(self, status: int, value: object) -> None:
        self._respond(status, json.dumps(value).encode(), "application/json; charset=utf-8")

    def _local(self, *, mutation: bool = False) -> bool:
        host = self.server.origin.removeprefix("http://")
        valid = self.headers.get_all("Host") == [host]
        if mutation:
            valid = (
                valid
                and self.headers.get("Origin") == self.server.origin
                and secrets.compare_digest(
                    self.headers.get("X-HOP-Editor-Token", ""), self.server.token
                )
            )
        if not valid:
            self._json(403, {"error": "Use this editor's local page and authorized action."})
        return valid

    def do_GET(self) -> None:
        if not self._local():
            return
        route = urlsplit(self.path).path
        session = self.server.session
        mode = (
            "design"
            if getattr(session, "mode", None) == "design"
            else "survey"
            if isinstance(session, SurveySession)
            else "variant"
            if isinstance(session, VariantSession)
            else "editor"
        )
        asset = asset_response(mode, route, self.server.token)
        if route == "/api/state":
            if mode == "design":
                design_session = cast("DesignInspectionSession", session)
                self._json(
                    200,
                    design_session.response(
                        design_session.state,
                        cohort=self.headers.get("X-HOP-Cohort"),
                        format=self.headers.get("X-HOP-Inspection"),
                    ),
                )
            else:
                self._json(200, session.state())
        elif asset is not None:
            self._respond(200, *asset)
        elif route.startswith("/files/"):
            relative = unquote(route.removeprefix("/files/"))
            path = PurePosixPath(relative)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in relative
                or path.as_posix() != relative
            ):
                self._json(400, {"error": "Invalid artifact path."})
                return
            target = self.server.session.root / path
            if any(p.is_symlink() for p in (target, *target.parents)) or not target.is_file():
                self._json(404, {"error": "No such generated artifact."})
                return
            self._respond(
                200,
                target.read_bytes(),
                mimetypes.guess_type(relative)[0] or "application/octet-stream",
            )
        else:
            self._json(404, {"error": "No such editor operation."})

    def do_POST(self) -> None:
        if not self._local(mutation=True):
            return
        try:
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                raise ValueError("One bounded Content-Length is required.")
            length = int(lengths[0])
            if not 0 < length <= 1_000_000 or self.headers.get_content_type() != "application/json":
                raise ValueError("Send a JSON action of at most one megabyte.")

            def distinct(pairs: list[tuple[str, object]]) -> dict[str, object]:
                result: dict[str, object] = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate JSON action field.")
                    result[key] = value
                return result

            body = json.loads(self.rfile.read(length), object_pairs_hook=distinct)
            if not isinstance(body, dict):
                raise ValueError("An editor action must be an object.")
            session = self.server.session
            if getattr(session, "mode", None) == "design":
                from ...design import inspection_discovery_actions as discovery
                from ...design.inspection_hover import cancel_neighbors, neighboring_preparations

                design_session = cast("DesignInspectionSession", session)
                if self.path == "/api/inspect-discovery":
                    self._json(
                        200,
                        discovery.inspect_results(
                            self.server,
                            design_session,
                            body,
                            format=self.headers.get("X-HOP-Inspection"),
                        ),
                    )
                    return
                actions: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
                    "/api/query": design_session.query,
                    "/api/select": design_session.select,
                    "/api/preview": design_session.preview,
                    "/api/scenes": design_session.scenes,
                    "/api/neighbors": lambda payload: neighboring_preparations(
                        design_session, payload
                    ),
                    "/api/cancel-neighbors": lambda payload: cancel_neighbors(
                        design_session, payload
                    ),
                    "/api/sample": design_session.sample,
                    "/api/retrieve": design_session.retrieve,
                    "/api/view": design_session.view,
                    "/api/restore": design_session.restore,
                    "/api/back": design_session.back,
                    "/api/family-stage": design_session.family_stage,
                    "/api/start-discovery": lambda p: discovery.start(design_session, p),
                    "/api/continue-discovery": lambda p: discovery.continue_work(design_session, p),
                    "/api/status-discovery": lambda p: discovery.status(design_session, p),
                    "/api/stop-discovery": lambda p: discovery.stop(design_session, p),
                }
                if self.path not in actions:
                    raise ValueError("Unknown inspection action.")
                self._json(
                    200,
                    design_session.response(
                        lambda: actions[self.path](body),
                        cohort=self.headers.get("X-HOP-Cohort"),
                        format=self.headers.get("X-HOP-Inspection"),
                    ),
                )
                return
            session = cast("EditorSession | VariantSession | SurveySession", session)
            if isinstance(session, SurveySession):
                actions = {
                    "/api/query": session.query,
                    "/api/select": session.select,
                    "/api/sample": session.sample,
                    "/api/retrieve": session.retrieve,
                    "/api/reload": session.reload,
                }
                if self.path not in actions:
                    raise ValueError("Unknown survey action.")
                self._json(200, actions[self.path](body))
                return
            operations = (
                {
                    "/api/query": session.query,
                    "/api/evaluate-parameters": session.evaluate_parameters,
                    "/api/preview-envelope": session.preview_envelope,
                    "/api/evaluate-envelope": session.evaluate_envelope,
                    "/api/parameter-domain": session.parameter_domain,
                    "/api/view": session.view,
                    "/api/inspect": session.inspect,
                    "/api/browse": session.browse,
                    "/api/compare": session.compare,
                    "/api/select-comparison": session.select_comparison,
                    "/api/select": session.select,
                }
                if isinstance(session, VariantSession)
                else {
                    "/api/preview": session.preview,
                    "/api/evaluate": session.evaluate,
                    "/api/select": session.select,
                }
            )
            if self.path not in operations:
                raise ValueError("Unknown editor action.")
            self._json(200, operations[self.path](body))
        except (OSError, ValueError) as error:
            self._json(400, {"error": str(error)})


def create_editor_server(
    request: Path,
    output: Path,
    *,
    port: int = 0,
    evaluated: bool = False,
    designs: construction.DesignChoices | None = None,
) -> EditorServer:
    session = (
        VariantSession(request, output, designs=designs)
        if evaluated
        else EditorSession(request, output)
    )
    try:
        return EditorServer(session, port)
    except BaseException:
        session.close()
        raise


def create_survey_server(
    request: Path,
    index: Path,
    output: Path,
    *,
    port: int = 0,
    discovery: dict[str, Any] | None = None,
    designs: construction.DesignChoices | None = None,
) -> EditorServer:
    session = SurveySession(request, index, output, discovery=discovery, designs=designs)
    try:
        return EditorServer(session, port)
    except BaseException:
        session.close()
        raise
