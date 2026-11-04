"""Local preview/evaluation adapters; the public HOP facade owns revision semantics."""

import json
import time
from typing import TYPE_CHECKING, Any

from hop_design import construction

if TYPE_CHECKING:
    from .variants import VariantSession


def preview_envelope(session: "VariantSession", payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"query_digest", "revision"}:
        raise ValueError("Envelope preview requires the current query and explicit revision.")
    with session._lock:
        session._current(payload["query_digest"])
        preview = construction.preview_scaffold_envelope_revision(
            session.pool, session._choices, payload["revision"]
        )
        preview.write(session._scene_destination("envelope-previews"))
        session._envelope_revision = preview
        session._state["envelope_revision"] = json.loads(preview.json_bytes)
        return session.state()


def evaluate_envelope(session: "VariantSession", payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {
        "query_digest",
        "revision_digest",
        "max_branches",
        "max_continuations_per_branch",
    }:
        raise ValueError("Envelope evaluation requires the current preview and explicit bounds.")
    with session._lock:
        session._current(payload["query_digest"])
        preview = session._envelope_revision
        if (
            preview is None
            or json.loads(preview.json_bytes)["revision_digest"] != payload["revision_digest"]
        ):
            raise ValueError(
                "Stale envelope preview; preview this revision with the current query."
            )
        started = time.perf_counter()
        packet = construction.evaluate_scaffold_envelope_revision(
            session.pool,
            preview,
            max_branches=payload["max_branches"],
            max_continuations_per_branch=payload["max_continuations_per_branch"],
        )
        session._adopt_evaluation(packet, session._scene_destination("envelope-evaluations"))
        session._envelope_revision = None
        session._state["envelope_revision"] = None
        session._state["timings"]["envelope_evaluation_seconds"] = time.perf_counter() - started
        return session.state()
