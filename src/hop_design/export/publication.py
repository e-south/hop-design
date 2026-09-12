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
import tempfile
from collections.abc import Mapping
from contextlib import ExitStack, suppress
from pathlib import Path
from uuid import uuid4


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


def _publish_darwin(staging: Path, destination: Path, *, parent_fd: int | None = None) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    arguments: tuple[int | bytes, ...]
    if parent_fd is None:
        rename = library.renamex_np
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        arguments = (os.fsencode(staging), os.fsencode(destination), 0x00000004)
    else:
        rename = library.renameatx_np
        rename.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        arguments = (
            parent_fd,
            os.fsencode(staging),
            parent_fd,
            os.fsencode(destination),
            0x00000004,
        )
    rename.restype = ctypes.c_int
    result = rename(*arguments)
    _raise_publication_error(result, destination)


def _publish_linux(staging: Path, destination: Path, *, parent_fd: int | None = None) -> None:
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
    directory = -100 if parent_fd is None else parent_fd
    result = rename(directory, os.fsencode(staging), directory, os.fsencode(destination), 1)
    _raise_publication_error(result, destination)


def publish_directory_create_only(
    staging: Path, destination: Path, *, parent_fd: int | None = None
) -> None:
    """Atomically publish one sibling directory without replacing any destination."""
    if parent_fd is None:
        staging = staging.absolute()
        destination = destination.absolute()
    elif any(
        path.parent != Path(".") or path.name in {"", ".", ".."} for path in (staging, destination)
    ):
        raise ValueError("Descriptor-bound publication requires immediate child names.")
    if staging.parent != destination.parent:
        raise ValueError("Directory publication requires sibling staging and destination paths.")
    if sys.platform == "darwin":
        _publish_darwin(staging, destination, parent_fd=parent_fd)
        return
    if sys.platform.startswith("linux"):
        _publish_linux(staging, destination, parent_fd=parent_fd)
        return
    if os.name == "nt" and parent_fd is None:
        os.rename(staging, destination)
        return
    raise OSError(
        errno.ENOTSUP,
        f"Atomic create-only directory publication is unsupported on {sys.platform}.",
        destination,
    )


def _open_publication_parent(destination: Path, protected_root: Path) -> int:
    """Bind the nearest existing parent before checking exclusion and creating children."""
    parent = destination.absolute().parent
    missing = []
    while not parent.exists():
        if parent.is_symlink():
            raise ValueError("Publication parent contains a dangling symlink.")
        missing.append(parent.name)
        parent = parent.parent
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(parent, flags)
    try:
        canonical = parent.resolve(strict=True)
        opened, named = os.fstat(descriptor), canonical.stat()
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            raise ValueError("Publication parent changed while it was being opened.")
        target = Path(os.path.normpath(canonical.joinpath(*reversed(missing), destination.name)))
        protected = protected_root.resolve(strict=True)
        if target == protected or target.is_relative_to(protected):
            raise ValueError("Output must be outside the verified input bundle.")
        for component in reversed(missing):
            with suppress(FileExistsError):
                os.mkdir(component, mode=0o755, dir_fd=descriptor)
            child = os.open(component, flags | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def publish_directory_files_create_only(
    files: Mapping[str, bytes], destination: Path, *, protected_root: Path
) -> None:
    """Publish flat artifact files through pinned directories outside one input authority."""
    if not (sys.platform == "darwin" or sys.platform.startswith("linux")):
        raise OSError(errno.ENOTSUP, "Protected publication requires directory descriptors.")
    if any(Path(name).name != name or name in {"", ".", ".."} for name in files):
        raise ValueError("Artifact publication requires immediate child filenames.")
    with ExitStack() as descriptors:
        parent_fd = _open_publication_parent(destination, protected_root)
        descriptors.callback(os.close, parent_fd)
        staging_name = f".{destination.name}.{uuid4().hex}"
        staging_fd = None
        created = False
        published = False
        written = []
        try:
            os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
            created = True
            staging_fd = os.open(
                staging_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
            )
            descriptors.callback(os.close, staging_fd)
            for name, content in files.items():
                descriptor = os.open(
                    name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=staging_fd
                )
                written.append(name)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            publish_directory_create_only(
                Path(staging_name), Path(destination.name), parent_fd=parent_fd
            )
            published = True
        finally:
            # Cleanup races must not replace the publication error or strand descriptors.
            if staging_fd is not None and not published:
                for name in written:
                    with suppress(OSError):
                        os.unlink(name, dir_fd=staging_fd)
            if created and not published:
                with suppress(OSError):
                    os.rmdir(staging_name, dir_fd=parent_fd)


def publish_file_create_only(content: bytes, destination: Path) -> None:
    """Atomically publish one sibling-staged file without replacing a destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staging_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
    )
    staging = Path(staging_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(staging, destination, follow_symlinks=False)
    finally:
        staging.unlink(missing_ok=True)


__all__ = [
    "publish_directory_create_only",
    "publish_directory_files_create_only",
    "publish_file_create_only",
]
