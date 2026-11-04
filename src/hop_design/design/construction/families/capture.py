"""Family inventory capture uses the bounded construction packet reader."""

from pathlib import Path

from hop_design.export.publication import ProtectedRoot

from ..packets.capture import capture_packet, write_snapshot


def capture_family(path: str | Path) -> tuple[ProtectedRoot, dict[str, bytes]]:
    return capture_packet(path, schema="hop.construction-family-packet/v1")


__all__ = ["capture_family", "write_snapshot"]
