"""Capture bounded family packets before interpreting any saved presentation facts."""

from pathlib import Path, PurePosixPath
from typing import Annotated

from pydantic import Field, field_validator

from hop_design.design.source_documents import _read_source_bytes
from hop_design.export.publication import ProtectedRoot
from hop_design.models.base import HopModel
from hop_design.serialization import canonical_json_bytes, sha256_digest

_MAX_BYTES = 512 * 1024 * 1024


class ConstructionManifest(HopModel):
    schema_id: str = Field(alias="schema")
    artifacts: dict[str, Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]]

    @field_validator("artifacts")
    @classmethod
    def safe_paths(cls, entries: dict[str, str]) -> dict[str, str]:
        if not entries or len(entries) > 20_000:
            raise ValueError("Family inventory must contain 1 to 20000 files.")
        for name in entries:
            p = PurePosixPath(name)
            if (
                not name
                or p.is_absolute()
                or ".." in p.parts
                or p.as_posix() != name
                or "\\" in name
                or name == "manifest.json"
            ):
                raise ValueError("Family artifact paths must be normalized and relative.")
        return entries


def capture_packet(path: str | Path, *, schema: str) -> tuple[ProtectedRoot, dict[str, bytes]]:
    root = ProtectedRoot.capture(Path(path))
    content = _read_source_bytes(
        root.path / "manifest.json", max_bytes=2_000_000, source_label="Family manifest"
    )
    manifest = ConstructionManifest.model_validate_json(content)
    if manifest.schema_id != schema:
        raise ValueError("Unsupported construction packet schema.")
    if canonical_json_bytes(manifest) != content:
        raise ValueError("Family manifest must use canonical JSON.")
    paths = tuple(root.path.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Family packet must not contain symlinks.")
    actual = {p.relative_to(root.path).as_posix() for p in paths if not p.is_dir()}
    if actual != {"manifest.json", *manifest.artifacts}:
        raise ValueError("Family packet files disagree with its inventory.")
    files = {"manifest.json": content}
    size = len(content)
    for name, digest in manifest.artifacts.items():
        data = _read_source_bytes(
            root.path / name, max_bytes=max(1, _MAX_BYTES - size), source_label="Family artifact"
        )
        size += len(data)
        if size > _MAX_BYTES or sha256_digest(data) != digest:
            raise ValueError("Family artifact size or digest disagrees with the inventory.")
        files[name] = data
    root.require_unchanged()
    return root, files


def write_snapshot(files: dict[str, bytes], root: Path) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
