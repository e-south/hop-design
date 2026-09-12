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
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping
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


def _write_file_at(content: bytes, name: str, parent_fd: int) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _write_directory_files_at(files: Mapping[str, bytes], staging_fd: int) -> None:
    directories = {Path("."): staging_fd}
    with ExitStack() as descriptors:
        for name, content in files.items():
            parent = Path(".")
            for component in Path(name).parts[:-1]:
                child = parent / component
                if child not in directories:
                    os.mkdir(component, mode=0o755, dir_fd=directories[parent])
                    descriptor = os.open(
                        component,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directories[parent],
                    )
                    descriptors.callback(os.close, descriptor)
                    directories[child] = descriptor
                parent = child
            _write_file_at(content, Path(name).name, directories[parent])


def _require_staging_directory(staging: Path, staging_fd: int) -> None:
    admitted, named = os.fstat(staging_fd), staging.stat(follow_symlinks=False)
    if (admitted.st_dev, admitted.st_ino) != (named.st_dev, named.st_ino):
        raise ValueError("Staged bundle path changed during verification.")


def publish_directory_files_create_only(
    files: Mapping[str, bytes],
    destination: Path,
    *,
    protected_root: Path,
    verifier: Callable[[Path], object] | None = None,
) -> None:
    """Publish artifact files through pinned directories outside one input authority."""
    if not (sys.platform == "darwin" or sys.platform.startswith("linux")):
        raise OSError(errno.ENOTSUP, "Protected publication requires directory descriptors.")
    if any(
        Path(name).is_absolute()
        or Path(name).as_posix() != name
        or name in {"", "."}
        or ".." in Path(name).parts
        for name in files
    ):
        raise ValueError("Artifact publication requires normalized relative file paths.")
    with ExitStack() as descriptors:
        parent_fd = _open_publication_parent(destination, protected_root)
        descriptors.callback(os.close, parent_fd)
        staging_name = f".{destination.name}.{uuid4().hex}"
        created = False
        published = False
        try:
            os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
            created = True
            staging_fd = os.open(
                staging_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
            )
            descriptors.callback(os.close, staging_fd)
            _write_directory_files_at(files, staging_fd)
            if verifier is not None:
                staging = destination.parent / staging_name
                _require_staging_directory(staging, staging_fd)
                verifier(staging)
                _require_staging_directory(staging, staging_fd)
            publish_directory_create_only(
                Path(staging_name), Path(destination.name), parent_fd=parent_fd
            )
            published = True
        finally:
            # Cleanup races must not replace the publication error or strand descriptors.
            if created and not published:
                with suppress(OSError):
                    shutil.rmtree(staging_name, dir_fd=parent_fd)


def _publish_protected_file(content: bytes, destination: Path, protected_root: Path) -> None:
    if not (sys.platform == "darwin" or sys.platform.startswith("linux")):
        raise OSError(errno.ENOTSUP, "Protected publication requires directory descriptors.")
    with ExitStack() as descriptors:
        parent_fd = _open_publication_parent(destination, protected_root)
        descriptors.callback(os.close, parent_fd)
        staging_name = f".{destination.name}.{uuid4().hex}"
        try:
            _write_file_at(content, staging_name, parent_fd)
            os.link(
                staging_name,
                destination.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        finally:
            with suppress(OSError):
                os.unlink(staging_name, dir_fd=parent_fd)


def publish_file_create_only(
    content: bytes, destination: Path, *, protected_root: Path | None = None
) -> None:
    """Atomically publish one sibling-staged file without replacing a destination."""
    if protected_root is not None:
        _publish_protected_file(content, destination, protected_root)
        return
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
