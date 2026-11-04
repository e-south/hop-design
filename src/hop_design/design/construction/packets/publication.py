"""Atomic deterministic construction packets; molecular authority remains in member bundles."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self

from hop_design.export.publication import (
    ProtectedRoot,
    publish_directory_create_only,
    publish_directory_files_create_only,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest


@dataclass(frozen=True, init=False, repr=False)
class ConstructionPacket:
    _packet_schema: ClassVar[str]
    _files: tuple[tuple[str, bytes], ...]
    _summary: bytes
    _report: str

    @classmethod
    def _create(cls, files: dict[str, bytes], summary: dict[str, object], report: str) -> Self:
        files = dict(files)
        files.pop("manifest.json", None)
        summary_bytes = canonical_json_bytes(summary)
        files.update({"summary.json": summary_bytes, "report.md": report.encode()})
        files["manifest.json"] = canonical_json_bytes(
            {
                "schema": cls._packet_schema,
                "artifacts": {
                    name: sha256_digest(content) for name, content in sorted(files.items())
                },
            }
        )
        instance = object.__new__(cls)
        object.__setattr__(instance, "_files", tuple(sorted(files.items())))
        object.__setattr__(instance, "_summary", summary_bytes)
        object.__setattr__(instance, "_report", report)
        return instance

    @property
    def json_bytes(self) -> bytes:
        return self._summary

    @property
    def report_text(self) -> str:
        return self._report

    def write(self, destination: str | Path) -> Path:
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing family path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            for name, content in self._files:
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != name:
                    raise ValueError("Family artifacts must use normalized relative paths.")
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output


@dataclass(frozen=True, init=False, repr=False)
class SourceBoundConstructionPacket(ConstructionPacket):
    """Publish derived family files outside their captured molecular authorities."""

    _roots: tuple[ProtectedRoot, ...]

    def write(self, destination: str | Path) -> Path:
        output = Path(destination)
        publish_directory_files_create_only(dict(self._files), output, protected_root=self._roots)
        return output
