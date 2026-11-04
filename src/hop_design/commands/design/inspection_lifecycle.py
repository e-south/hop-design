"""Release inspection drawings and background work independently of saved results."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .inspection import DesignInspectionSession


def close_inspection(session: "DesignInspectionSession", *, close_discovery: bool = True) -> None:
    if close_discovery:
        session._discovery.close()
    session._hover.stop()
    with session._lock:
        session._neighbor_cancel.set()
        session._state.clear()
        session._undo.clear()
        session._history.clear()
        session._cache.close()
        session._plots.close()
        session._hover.close()
    if not session._neighbor_done.wait(timeout=2):
        raise RuntimeError("Neighbor work did not stop within two seconds of closing.")
