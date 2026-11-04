"""One lazy, owned process for bounded inspection work; no queued hover jobs."""

import multiprocessing
from collections.abc import Callable
from math import isfinite
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from threading import Event, Lock
from time import monotonic
from typing import cast


def _invoke[Request, Result](
    function: Callable[[Request], Result], request: Request
) -> tuple[bool, Result | str]:
    try:
        return True, function(request)
    except Exception as error:
        # Validation exceptions need not be pickleable to reach the local inspector.
        return False, f"{type(error).__name__}: {error}"


def _serve[Request, Result](connection: Connection, function: Callable[[Request], Result]) -> None:
    try:
        while True:
            connection.send(_invoke(function, connection.recv()))
    except EOFError:
        pass
    finally:
        connection.close()


class SingleWorker[Request, Result]:
    def __init__(self, function: Callable[[Request], Result]) -> None:
        self._function = function
        self._process: BaseProcess | None = None
        self._connection: Connection | None = None
        self._guard, self._busy = Lock(), Lock()
        self._closed = Event()

    def call(self, request: Request, *, timeout: float = 10) -> Result:
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("Inspection worker timeout must be finite and positive.")
        if not self._busy.acquire(blocking=False):
            raise ValueError("The inspection renderer is busy; retry the latest preview.")
        try:
            deadline = monotonic() + timeout
            with self._guard:
                self._check_open()
                if self._process is None:
                    context = multiprocessing.get_context("spawn")
                    parent, child = context.Pipe()
                    process = context.Process(target=_serve, args=(child, self._function))
                    try:
                        process.start()
                    except BaseException:
                        parent.close()
                        child.close()
                        raise
                    child.close()
                    self._connection, self._process = parent, process
                connection = self._connection
                assert connection is not None
            connection.send(request)
            while True:
                self._check_open()
                remaining = deadline - monotonic()
                if remaining <= 0:
                    self._dispose()
                    raise ValueError("Molecular preview timed out; retry to start a new renderer.")
                if not connection.poll(min(0.05, remaining)):
                    continue
                success, result = connection.recv()
                self._check_open()
                if not success:
                    raise ValueError(f"Molecular preview failed: {result}")
                return cast(Result, result)
        except (EOFError, OSError) as error:
            self._dispose()
            self._check_open()
            raise ValueError(
                "Molecular renderer stopped unexpectedly; retry to restart it."
            ) from error
        finally:
            self._busy.release()

    def _check_open(self) -> None:
        if self._closed.is_set():
            raise ValueError("The inspection renderer is closed.")

    def _dispose(self) -> None:
        with self._guard:
            process, self._process = self._process, None
            connection, self._connection = self._connection, None
        if process is not None:
            # No shared queues or locks: a killed worker cannot strand a pool
            # management thread. Discard its private pipe before any retry.
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()
        if connection is not None:
            connection.close()

    def close(self) -> None:
        self._closed.set()
        self._dispose()
