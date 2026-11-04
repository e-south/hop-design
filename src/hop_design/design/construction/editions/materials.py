"""Lossless per-preparation storage; inspect one authority at a time."""

import io
import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.editions.manifest import artifact_path
from hop_design.serialization import canonical_json_bytes

from .storage import DirectoryFiles

if TYPE_CHECKING:
    from .reader import AtlasEdition

MAX_MEMBER_BYTES = 256 * 1024 * 1024


def archive_materials(root: Path, destination: Path) -> None:
    files = DirectoryFiles(root)
    size = sum((root / name).stat().st_size for name in files)
    if size > MAX_MEMBER_BYTES:
        raise ValueError("Captured preparation exceeds the 256 MiB authority limit.")
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name in files:
            item = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = ZIP_DEFLATED
            item.external_attr = 0o100600 << 16
            archive.writestr(item, files[name])


class ArchivedMaterials(Mapping[str, bytes]):
    """Digest-checked archive with bounded expansion and no extraction to disk."""

    def __init__(self, content: bytes):
        self._content = content
        with ZipFile(io.BytesIO(content)) as archive:
            records = archive.infolist()
            names = [artifact_path(record.filename) for record in records]
            if len(names) != len(set(names)):
                raise ValueError("Captured material archive has duplicate paths.")
            if sum(record.file_size for record in records) > MAX_MEMBER_BYTES:
                raise ValueError("Captured preparation exceeds the 256 MiB authority limit.")
            if any(
                record.is_dir() or (record.external_attr >> 16) & 0o170000 != 0o100000
                for record in records
            ):
                raise ValueError("Captured materials must be ordinary files.")
            self._names = frozenset(names)

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._names))

    def __len__(self) -> int:
        return len(self._names)

    def __getitem__(self, name: str) -> bytes:
        if name not in self._names:
            raise KeyError(name)
        with ZipFile(io.BytesIO(self._content)) as archive:
            return archive.read(name)


def member_materials(edition: "AtlasEdition", identity: str) -> Mapping[str, bytes]:
    prefix = edition._prefix(identity)
    if edition._store.compact:
        return ArchivedMaterials(edition._store.read(prefix + "/evidence.zip"))
    return edition._store.files(prefix + "/materials/")


def route_from_materials(
    files: Mapping[str, bytes], identity: str
) -> MaterializedConstructionRealization:
    return MaterializedConstructionRealization.model_validate_json(
        route_record_from_materials(files, identity)
    )


def route_record_from_materials(files: Mapping[str, bytes], identity: str) -> bytes:
    """Extract one record; callers must still validate its molecular authority."""
    for name in files:
        if name.endswith("/construction-result.json"):
            raw = json.loads(files[name])
            for route in raw.get("realizations", ()):
                if route.get("materialized_realization_id") == identity:
                    return canonical_json_bytes(route)
    raise ValueError("Captured materials lack the selected complete route record.")
