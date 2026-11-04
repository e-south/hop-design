"""Invocation-owned observers and cooperative stopping, outside molecular identity."""

from collections.abc import Callable
from dataclasses import dataclass

from hop_design.models.construction.intents.progress import DiscoveryProgress

type ProgressObserver = Callable[[DiscoveryProgress], None]
type StopRequest = Callable[[], bool]


class DiscoveryCancelled(RuntimeError):
    """Stopped before a first result snapshot; saved intent can be continued."""


@dataclass(frozen=True)
class DiscoveryFeedback:
    on_progress: ProgressObserver | None = None
    should_stop: StopRequest | None = None

    def __post_init__(self) -> None:
        for callback in (self.on_progress, self.should_stop):
            if callback is not None and not callable(callback):
                raise TypeError("Discovery feedback requires callable observers and stop checks.")

    def stop_requested(self) -> bool:
        if self.should_stop is None:
            return False
        requested = self.should_stop()
        if type(requested) is not bool:
            raise TypeError("The discovery stop check must return a Boolean.")
        return requested

    def emit(self, event: DiscoveryProgress) -> None:
        if self.on_progress is not None:
            self.on_progress(event)
