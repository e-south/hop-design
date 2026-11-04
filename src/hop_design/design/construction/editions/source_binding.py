"""Stream-check a recorded source without admitting execution or mutating its files."""

from hashlib import sha256
from pathlib import Path

from hop_design.models.construction.editions.source import RecordedDesignSource


def verify_source(root: Path, source: RecordedDesignSource) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Recorded source must be an existing regular directory.")
    if (root / "family").exists():
        raise ValueError("Capture exact-member discoveries separately.")
    if any((root / ("survey.sqlite" + suffix)).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError(
            "Recorded capture requires a quiescent checkpoint without SQLite sidecars."
        )
    actual = {"survey.sqlite", "effort.json"}
    for name in ("intent", "revision"):
        directory = root / name
        if not directory.exists():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Recorded inputs must be regular, contained files.")
        for path in directory.rglob("*"):
            if path.is_symlink() or not path.is_relative_to(root):
                raise ValueError("Recorded inputs must be regular, contained files.")
            if path.is_file():
                actual.add(path.relative_to(root).as_posix())
            elif not path.is_dir():
                raise ValueError("Recorded input is not a regular file or directory.")
    if actual != source.files.keys():
        raise ValueError("Bind exactly the complete recorded input set.")
    for name, expected in source.files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != expected.bytes:
            raise ValueError(f"Recorded source file or size changed: {name}")
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if "sha256:" + digest.hexdigest() != expected.sha256:
            raise ValueError(f"Recorded source digest changed: {name}")
