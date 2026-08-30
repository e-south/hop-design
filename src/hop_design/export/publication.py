"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/publication.py

Publishes complete directory trees atomically without replacing a destination.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import ctypes
import errno
import os
import sys
from pathlib import Path


def _raise_publication_error(result: int, destination: Path) -> None:
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(
            error_number,
            os.strerror(error_number),
            destination,
        )
    raise OSError(error_number, os.strerror(error_number), destination)


def _publish_darwin(staging: Path, destination: Path) -> None:
    rename = ctypes.CDLL(None, use_errno=True).renamex_np
    rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    result = rename(os.fsencode(staging), os.fsencode(destination), 0x00000004)
    _raise_publication_error(result, destination)


def _publish_linux(staging: Path, destination: Path) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    try:
        rename = library.renameat2
    except AttributeError as error:
        raise OSError(
            errno.ENOTSUP,
            "Atomic create-only directory publication requires renameat2.",
            destination,
        ) from error
    rename.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    rename.restype = ctypes.c_int
    result = rename(-100, os.fsencode(staging), -100, os.fsencode(destination), 1)
    _raise_publication_error(result, destination)


def publish_directory_create_only(staging: Path, destination: Path) -> None:
    """Atomically publish one sibling directory without replacing any destination."""
    if staging.parent != destination.parent:
        raise ValueError("Directory publication requires sibling staging and destination paths.")
    if sys.platform == "darwin":
        _publish_darwin(staging, destination)
        return
    if sys.platform.startswith("linux"):
        _publish_linux(staging, destination)
        return
    if os.name == "nt":
        os.rename(staging, destination)
        return
    raise OSError(
        errno.ENOTSUP,
        f"Atomic create-only directory publication is unsupported on {sys.platform}.",
        destination,
    )


__all__ = ["publish_directory_create_only"]
