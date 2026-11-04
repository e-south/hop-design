"""One local inspection adapter over live choices and captured atlas editions."""

import copy
import threading
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from hop_design import construction

from .inspection_cache import PreviewCache, state_key
from .inspection_discovery import DiscoveryWork, default_request
from .inspection_handoff import preparation_download
from .inspection_hover import HoverCache
from .inspection_lifecycle import close_inspection
from .inspection_plots import InspectionPlots
from .inspection_response import prepare_selection, preview_response, state_response
from .inspection_sampling import sample_preparation
from .inspection_view import (
    history_frame,
    initial_state,
    requires_redraw,
    unselected_presentation,
)


class DesignInspectionSession:
    mode = "design"

    def __init__(
        self, choices: construction.DesignChoices | construction.AtlasEdition, output: Path
    ) -> None:
        if any(p.is_symlink() for p in (output, *output.parents)):
            raise ValueError("Inspection output cannot use symbolic links.")
        if output.resolve().is_relative_to(choices._directory):
            raise ValueError("Write inspection output outside the recorded choices.")
        output.mkdir(parents=True, exist_ok=False)
        self.root = output.resolve()
        self.designs = choices
        self._discovery = DiscoveryWork(self.root)
        self._discovery_request = default_request(choices.resolution)
        self._cache = PreviewCache(self.root)
        self._plots = InspectionPlots(self.root)
        self._hover = HoverCache(self.root)
        self.cache_root = self._cache.root
        self._lock = threading.RLock()
        self._undo: list[dict[str, Any]] = []
        self._history: list[str] = []
        self._serial = 0
        self._transport_cohort: ContextVar[str | None] = ContextVar(
            "transport_cohort", default=None
        )
        self._transport_format: ContextVar[str | None] = ContextVar(
            "transport_format", default=None
        )
        self._neighbor_cancel = threading.Event()
        self._neighbor_request: str | None = None
        self._neighbor_lock = threading.Lock()
        self._neighbor_done = threading.Event()
        self._neighbor_done.set()
        self._state = initial_state(choices)
        self._token()

    def _token(self) -> None:
        self._neighbor_cancel.set()
        self._serial += 1
        self._state["token"] = state_key([self._state["choices"]["snapshot_digest"], self._serial])

    @contextmanager
    def _action(self) -> Iterator[None]:
        with self._lock:
            previous = (dict(self._state), list(self._undo), list(self._history), self._serial)
            try:
                yield
            except BaseException:
                self._state, self._undo, self._history, self._serial = previous
                raise

    def _check(
        self, payload: dict[str, Any], required: Iterable[str] = (), optional: Iterable[str] = ()
    ) -> None:
        if not set(required) <= payload.keys() or set(payload) - {"token", *required, *optional}:
            raise ValueError("Inspection action has missing or unknown fields.")
        if not self._state or payload.get("token") != self._state["token"]:
            raise ValueError("Stale inspection; use the current view.")

    def _remember(self) -> None:
        # Only receipts/history are retained, never route scenes or SVG copies.
        self._undo.append(history_frame(self._state, self._history))
        self._undo = self._undo[-32:]

    def response(
        self,
        action: Callable[[], dict[str, Any]],
        *,
        cohort: str | None = None,
        format: str | None = None,
    ) -> dict[str, Any]:
        """Omit an unchanged cohort only for this authorized transport request.

        The hint never admits a selection or skips an action check. Each action
        owns its state lock; this request-local hint cannot leak between clients
        or hold that lock during independent comparison work.
        """
        if format not in {None, "compact-v1"}:
            raise ValueError("Unknown browser inspection transport.")
        token = self._transport_cohort.set(cohort)
        format_token = self._transport_format.set(format)
        try:
            return action()
        finally:
            self._transport_cohort.reset(token)
            self._transport_format.reset(format_token)

    def state(self) -> dict[str, Any]:
        with self._lock:
            result = state_response(
                self._state,
                self.designs,
                self.root,
                self._plots,
                transport_cohort=self._transport_cohort.get(),
                can_back=bool(self._undo),
                compact=self._transport_format.get() == "compact-v1",
            )
            result["cache"] = {
                "retained_bytes": self._cache.bytes + self._plots.bytes + self._hover.bytes,
                "byte_limit": self._cache.byte_limit
                + self._plots.byte_limit
                + self._hover.byte_limit,
            }
            result["discovery_request"] = copy.deepcopy(self._discovery_request)
            result["discovery_work"] = self._discovery.snapshot()
            return result

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, {"materialized_realization_id"}, {"phases"})
            return preview_response(
                self._state,
                self.designs,
                self._plots,
                self._hover,
                payload["materialized_realization_id"],
                phases=payload.get("phases"),
            )

    def scenes(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, {"materialized_realization_id", "phases"})
            result = self._hover.scenes(
                self.designs,
                payload["materialized_realization_id"],
                self._state["choices"],
                payload["phases"],
                presentation=self._state["presentation"]["route"],
                render_policy=self._state["render_policy"],
            )
            return {**result, "token": self._state["token"]}

    def _show(
        self,
        selected: dict[str, Any],
        *,
        reference: dict[str, Any] | None = None,
        receipt: dict[str, Any] | None = None,
        restore: dict[str, Any] | None = None,
    ) -> None:
        updates, history = prepare_selection(
            self._state,
            self.designs,
            self._cache,
            selected,
            self._history,
            reference=reference,
            receipt=receipt,
            restore=restore,
        )
        self._state.update(updates)
        self._history = history
        self._token()

    def sample(self, payload: dict[str, Any]) -> dict[str, Any]:
        return sample_preparation(self, payload)

    def select(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload, {"materialized_realization_id"})
            selected = self.designs.select(
                payload["materialized_realization_id"], query=self._state["choices"]["query"]
            )
            self._remember()
            self._show(selected, reference=self._state["selection"])
            return self.state()

    def query(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload, {"query"})
            choices = self.designs.query(payload["query"])
            self._remember()
            old = self._state["selection"] or (self._state["view_receipt"] or {}).get("selection")
            self._state.update(
                choices=choices,
                selection=None,
                handoff=None,
                sample_receipt=None,
                preview_status="excluded_by_query" if self._state["preview"] else None,
            )
            if old:
                try:
                    selected = self.designs.select(
                        old["materialized_realization_id"], query=choices["query"]
                    )
                except ValueError:
                    pass
                else:
                    self._show(selected)
            self._token()
            return self.state()

    def family_stage(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload, {"stage"})
            self.designs.families(query=self._state["choices"]["query"], stage=payload["stage"])
            self._state["family_stage"] = payload["stage"]
            self._state["presentation"] = {
                **self._state["presentation"],
                "family_stage": payload["stage"],
            }
            if self._state["selection"] is not None:
                current = self._state["view_receipt"]
                return self.view(
                    {
                        "token": payload["token"],
                        "stage": current["stage"],
                        "camera": current["camera"],
                    }
                )
            self._token()
            return self.state()

    def view(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload, {"stage", "camera"}, {"presentation", "render_policy"})
            if self._state["selection"] is None:
                self._state.update(
                    unselected_presentation(self.designs, payload, self._state["presentation"])
                )
                self._token()
                return self.state()
            current = self._state["view_receipt"]
            receipt = self.designs.view(
                self._state["selection"],
                stage=payload["stage"],
                camera=payload["camera"],
                reference_identity=current["reference_identity"],
                presentation=payload.get("presentation", self._state["presentation"]),
                exploration={**self._state["exploration"], "history": self._history},
                render_policy=payload.get("render_policy", current["render_policy"]),
            )
            if requires_redraw(current, receipt):
                self._remember()
                reference = (
                    self.designs.select(receipt["reference_identity"])
                    if receipt["reference_identity"]
                    else None
                )
                self._show(receipt["selection"], reference=reference, restore=receipt)
            self._state.update(
                stage=receipt["stage"],
                view_receipt=receipt,
                presentation=receipt["presentation"],
                family_stage=receipt["presentation"]["family_stage"],
            )
            self._token()
            return self.state()

    def restore(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload, {"receipt"})
            receipt = self.designs.restore_view(payload["receipt"])
            self._remember()
            self._state["choices"] = self.designs.query(receipt["selection"].get("query"))
            reference = (
                self.designs.select(receipt["reference_identity"])
                if receipt["reference_identity"]
                else None
            )
            self._show(receipt["selection"], reference=reference, restore=receipt)
            return self.state()

    def back(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload)
            if not self._undo:
                raise ValueError("No preceding inspection remains.")
            previous = self._undo.pop()
            self._state["choices"] = self.designs.query(previous["query"])
            receipt = previous["view_receipt"]
            if receipt:
                reference = (
                    self.designs.select(receipt["reference_identity"])
                    if receipt["reference_identity"]
                    else None
                )
                self._show(
                    receipt["selection"],
                    reference=reference,
                    restore=receipt,
                    receipt=previous["sample_receipt"],
                )
                if not previous["eligible"]:
                    self._state.update(selection=None, preview_status="excluded_by_query")
            else:
                self._state.update(
                    selection=None,
                    preview=None,
                    view_receipt=None,
                    sample_receipt=None,
                    stage="all",
                    preview_status=None,
                    handoff=None,
                )
            self._state["family_stage"] = previous["family_stage"]
            self._history = list(previous["history"])
            self._state["presentation"] = previous["presentation"]
            self._state["exploration"] = previous["exploration"]
            self._state["render_policy"] = previous["render_policy"]
            self._token()
            return self.state()

    def retrieve(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._action():
            self._check(payload, {"selection"})
            selected = self._state["selection"]
            if selected is None or payload["selection"] != selected:
                raise ValueError("Retrieve the current eligible preparation.")
            self._state["handoff"] = preparation_download(self.designs, self.root, selected)
            return self.state()

    def close(self, *, close_discovery: bool = True) -> None:
        close_inspection(self, close_discovery=close_discovery)
