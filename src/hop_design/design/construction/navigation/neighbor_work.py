"""Invocation-owned cancellation and elapsed-time bounds for neighbor inspection."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from math import isfinite
from threading import Event
from time import monotonic


class NeighborStopped(ValueError):
    """Stopped work has no completed comparison result."""


class NeighborWork:
    def __init__(self, seconds: float = 5.0, *, cancelled: Event | None = None):
        if isinstance(seconds, bool) or not isfinite(seconds) or not 0 < seconds <= 300:
            raise ValueError(
                "Neighbor inspection requires a time budget above zero, at most 300 s."
            )
        self.cancelled = cancelled if cancelled is not None else Event()
        self.deadline = monotonic() + seconds

    @contextmanager
    def activate(self) -> Iterator[None]:
        """Carry cancellation through nested shared preservation queries."""
        token = _current_work.set(self)
        try:
            self.check()
            yield
        finally:
            _current_work.reset(token)

    def check(self) -> None:
        if self.cancelled.is_set():
            raise NeighborStopped("Neighbor inspection cancelled; no comparison result committed.")
        if monotonic() >= self.deadline:
            raise NeighborStopped(
                "Neighbor inspection exceeded its time budget; results are unresolved."
            )


_current_work: ContextVar[NeighborWork | None] = ContextVar("neighbor_work", default=None)


def check_neighbor_work() -> None:
    """No budget is imposed on ordinary queries outside neighbor inspection."""
    if work := _current_work.get():
        work.check()
