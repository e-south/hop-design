"""Opt-in progress on stderr; one interrupt requests a safe checkpoint stop."""

import signal
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Event
from typing import Any

import typer

from hop_design.construction import DiscoveryCancelled, DiscoveryProgress


@contextmanager
def execution_feedback(enabled: bool) -> Iterator[dict[str, Any]]:
    if not enabled:
        yield {}
        return
    stopped = Event()
    previous = signal.getsignal(signal.SIGINT)

    def interrupt(signum: int, frame: object) -> None:
        if stopped.is_set():
            raise KeyboardInterrupt
        stopped.set()
        typer.echo(
            "Stopping after the current molecular evaluation; saved work is retained.", err=True
        )

    def observe(event: DiscoveryProgress) -> None:
        typer.echo(event.model_dump_json(by_alias=True), err=True)

    signal.signal(signal.SIGINT, interrupt)
    try:
        yield {"on_progress": observe, "should_stop": stopped.is_set}
    except DiscoveryCancelled as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(130) from error
    finally:
        signal.signal(signal.SIGINT, previous)
