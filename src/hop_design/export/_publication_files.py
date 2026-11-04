"""Write a staged tree with descriptor usage bounded by path depth."""

import os
from collections.abc import Mapping
from pathlib import Path


def _write_file_at(content: bytes, name: str, parent_fd: int) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _write_directory_files_at(files: Mapping[str, bytes], staging_fd: int) -> None:
    # Component ordering keeps each subtree contiguous: closed directories are
    # never reopened by pathname, and active ancestors remain descriptor-pinned.
    directories = [staging_fd]
    active: tuple[str, ...] = ()
    try:
        for name in sorted(files, key=lambda name: Path(name).parts):
            parts = Path(name).parts
            parent = parts[:-1]
            common = 0
            for left, right in zip(active, parent, strict=False):
                if left != right:
                    break
                common += 1
            while len(directories) > common + 1:
                os.close(directories.pop())
            for component in parent[common:]:
                os.mkdir(component, mode=0o755, dir_fd=directories[-1])
                directories.append(
                    os.open(
                        component,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directories[-1],
                    )
                )
            active = parent
            _write_file_at(files[name], parts[-1], directories[-1])
    finally:
        while len(directories) > 1:
            os.close(directories.pop())
