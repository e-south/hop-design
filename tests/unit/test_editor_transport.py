"""A pressured local socket must neither truncate nor duplicate molecular artwork."""

import errno

import pytest

from hop_design.commands.construction.editor import server


def test_large_response_preserves_exact_bytes_across_partial_send_and_buffer_pressure(monkeypatch):
    class Socket:
        def __init__(self):
            self.received = bytearray()
            self.calls = 0
            self.largest_chunk = 0

        def send(self, data):
            self.calls += 1
            self.largest_chunk = max(self.largest_chunk, len(data))
            if self.calls in (2, 3):
                raise OSError(errno.ENOBUFS, "No buffer space available")
            count = min(117, len(data)) if self.calls == 1 else len(data)
            self.received.extend(data[:count])
            return count

        def gettimeout(self):
            return 15

        def settimeout(self, value):
            pass

    sleeps = []
    monkeypatch.setattr(server.time, "sleep", sleeps.append)
    connection = Socket()
    body = bytes(range(256)) * 20_000
    server.send_response_body(connection, body)
    assert bytes(connection.received) == body
    assert connection.largest_chunk <= 64 * 1024
    assert sleeps == [0.01, 0.02]


def test_permanent_pressure_has_a_deadline_and_other_socket_errors_are_not_retried(monkeypatch):
    class Socket:
        def __init__(self, error):
            self.error = error

        def send(self, data):
            raise OSError(self.error, "injected socket failure")

        def gettimeout(self):
            return 15

        def settimeout(self, value):
            pass

    clock = iter((0.0, 0.1, 16.0))
    sleeps = []
    monkeypatch.setattr(server.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(server.time, "sleep", sleeps.append)
    with pytest.raises(TimeoutError, match="deadline"):
        server.send_response_body(Socket(errno.ENOBUFS), b"exact")
    assert sleeps == [0.01]

    monkeypatch.setattr(server.time, "monotonic", lambda: 0.0)
    sleeps.clear()
    with pytest.raises(OSError) as failure:
        server.send_response_body(Socket(errno.ECONNRESET), b"exact")
    assert failure.value.errno == errno.ECONNRESET
    assert sleeps == []
