"""Authorized discovery actions and an atomic, same-server inspection transition."""

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hop_design import construction

from .inspection import DesignInspectionSession

if TYPE_CHECKING:
    from ..construction.editor.server import EditorServer


def start(session: DesignInspectionSession, payload: dict[str, Any]) -> dict[str, Any]:
    with session._lock:
        session._check(payload, {"request", "evaluations"}, {"first_choices"})
    return session._discovery.begin(
        payload["request"],
        evaluations=payload["evaluations"],
        first_choices=payload.get("first_choices"),
    )


def _check_payload(payload: dict[str, Any], *, continuation: bool = False) -> None:
    # HTTP authorization remains required. Job identity survives pin/query changes.
    required = {"token", "job_id", *({"evaluations"} if continuation else set())}
    optional = {"first_choices"} if continuation else set()
    if not required <= payload.keys() or payload.keys() - required - optional:
        raise ValueError("Discovery action has missing or unknown fields.")
    if not isinstance(payload["job_id"], str) or not isinstance(payload["token"], str):
        raise ValueError("Use this session's current discovery identifier.")


def continue_work(session: DesignInspectionSession, payload: dict[str, Any]) -> dict[str, Any]:
    _check_payload(payload, continuation=True)
    return session._discovery.begin(
        None,
        evaluations=payload["evaluations"],
        first_choices=payload.get("first_choices"),
        previous=payload["job_id"],
    )


def status(session: DesignInspectionSession, payload: dict[str, Any]) -> dict[str, Any]:
    _check_payload(payload)
    result = session._discovery.snapshot(payload["job_id"])
    assert result is not None
    return result


def stop(session: DesignInspectionSession, payload: dict[str, Any]) -> dict[str, Any]:
    _check_payload(payload)
    return session._discovery.stop(payload["job_id"])


def _initial_selection(
    candidate: DesignInspectionSession, previous: dict[str, Any] | None
) -> dict[str, Any]:
    identity = previous.get("materialized_realization_id") if previous else None
    if identity and any(
        path["matches"] and path["materialized_realization_id"] == identity
        for path in candidate._state["choices"]["paths"]
    ):
        return candidate.select(
            {"token": candidate._state["token"], "materialized_realization_id": identity}
        )
    return candidate.sample(
        {"token": candidate._state["token"], "seed": 0, "strategy": "preparations"}
    )


def inspect_results(
    server: "EditorServer",
    original: DesignInspectionSession,
    payload: dict[str, Any],
    *,
    format: str | None = None,
) -> dict[str, Any]:
    """Admit and render before changing the active session; keep search ownership."""
    _check_payload(payload)
    with original._lock:
        original._check(payload, {"job_id"})
        previous = original._state["selection"]
    controller = original._discovery
    with controller.inspectable_result(payload["job_id"]) as directory:
        choices = construction.load_design_choices(directory)
        staging = Path(tempfile.mkdtemp(prefix="inspection-", dir=controller.output_directory))
        candidate = None
        committed = False
        try:
            candidate = DesignInspectionSession(choices, staging / "view")
            result = candidate.response(
                lambda: _initial_selection(candidate, previous), format=format
            )
            with server._inspection_transition, original._lock:
                if server._closing:
                    raise ValueError("This inspection server is closed.")
                if server.session is not original:
                    raise ValueError("Stale inspection; use the current view.")
                original._check(payload, {"job_id"})
                result["discovery_work"] = controller.snapshot(payload["job_id"])
                candidate._discovery.close()
                candidate._discovery = controller
                server.session = candidate
                committed = True
            try:
                original.close(close_discovery=False)
            except RuntimeError as error:
                # The switch has committed: do not return an error with the old token.
                result["inspection_notice"] = f"Results opened; earlier view cleanup: {error}"
            return result
        finally:
            if not committed:
                if candidate is not None:
                    candidate.close()
                shutil.rmtree(staging)
