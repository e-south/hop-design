"""Integrity-checked, lazy edition reads and bounded-memory publication."""

from collections.abc import Iterator, Mapping
from pathlib import Path

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.editions.manifest import AtlasEditionManifest, artifact_path
from hop_design.serialization import sha256_digest


class DirectoryFiles(Mapping[str, bytes]):
    """Read one staging file at a time during atomic publication."""

    def __init__(self, root: Path):
        self.root = root
        self.names = inventory(root)

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self.names))

    def __len__(self) -> int:
        return len(self.names)

    def __getitem__(self, name: str) -> bytes:
        if name not in self.names:
            raise KeyError(name)
        return (self.root / name).read_bytes()


def inventory(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Edition root must be an ordinary directory.")
    names = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Edition artifacts cannot be symlinks.")
        if path.is_file():
            names.add(artifact_path(path.relative_to(root).as_posix()))
        elif not path.is_dir():
            raise ValueError("Edition artifacts must be ordinary files.")
    return names


class EditionStore:
    def __init__(self, directory: str | Path):
        root = Path(directory)
        names = inventory(root)
        self.root = ProtectedRoot.capture(root)
        raw = (root / "edition.json").read_bytes()
        self.manifest = AtlasEditionManifest.model_validate_json(raw)
        self.digest = sha256_digest(raw)
        if names != set(self.manifest.artifacts) | {"edition.json"}:
            raise ValueError("Edition inventory has missing or unmanifested artifacts.")
        # v1 preserves its full byte-validation contract. v2 validates metadata
        # now and each compressed authority on access; it never claims a replay.
        for name in sorted(self.manifest.artifacts):
            if self.compact and name.endswith("/evidence.zip"):
                if (root / name).stat().st_size != self.manifest.artifacts[name].bytes:
                    raise ValueError(f"Edition artifact size disagrees: {name}")
                continue
            self.read(name)

    @property
    def compact(self) -> bool:
        return self.manifest.schema_id == "hop.atlas-edition/v2"

    def read(self, name: str) -> bytes:
        artifact_path(name)
        record = self.manifest.artifacts.get(name)
        if record is None:
            raise ValueError("Artifact is not part of this edition.")
        self.root.require_unchanged()
        current = self.root.path
        for part in Path(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Edition artifact became a symlink.")
        content = current.read_bytes()
        if len(content) != record.bytes or sha256_digest(content) != record.sha256:
            raise ValueError(f"Edition artifact digest disagrees: {name}")
        return content

    def files(self, prefix: str) -> Mapping[str, bytes]:
        store = self
        names = {n.removeprefix(prefix) for n in self.manifest.artifacts if n.startswith(prefix)}

        class MemberFiles(Mapping[str, bytes]):
            def __iter__(self) -> Iterator[str]:
                return iter(sorted(names))

            def __len__(self) -> int:
                return len(names)

            def __getitem__(self, name: str) -> bytes:
                if name not in names:
                    raise KeyError(name)
                return store.read(prefix + name)

        return MemberFiles()
