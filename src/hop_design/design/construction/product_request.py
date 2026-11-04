"""Prepare portable construction inputs from one strict product request."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.product_request import render_product_request
from hop_design.export.construction.request_preview import preview_product_request
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes


@dataclass(frozen=True, init=False, repr=False)
class PreparedConstructionRequest:
    """Immutable translated inputs, explicitly without discovery or verification claims."""

    _authored: bytes
    _source: bytes
    _report: str
    _preview: bytes

    @classmethod
    def _create(cls, authored: bytes, source: bytes, report: str, preview: bytes) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_authored", authored)
        object.__setattr__(instance, "_source", source)
        object.__setattr__(instance, "_report", report)
        object.__setattr__(instance, "_preview", preview)
        return instance

    @property
    def request_json_bytes(self) -> bytes:
        """Return the authored input, without replacing it with derived construction fields."""
        return self._authored

    @property
    def source_json_bytes(self) -> bytes:
        """Return canonical hop.construction-source/v8 input for existing compilers."""
        return self._source

    @property
    def report_text(self) -> str:
        """Describe required, derived and unresolved values without claiming feasibility."""
        return self._report

    @property
    def preview_json_bytes(self) -> bytes:
        """Return request-bound unevaluated footprint and permission facts."""
        return self._preview

    def write(self, destination: str | Path) -> Path:
        """Atomically publish the authored request and expanded inputs to a new directory."""
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing request path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            (staging / "request.json").write_bytes(self._authored)
            (staging / "construction.json").write_bytes(self._source)
            (staging / "intent.md").write_text(self._report, encoding="utf-8")
            (staging / "preview.json").write_bytes(self._preview)
            source = json.loads(self._source)
            for family in ("foldback", "basal"):
                if source[family] is not None:
                    (staging / f"{family}.json").write_bytes(canonical_json_bytes(source[family]))
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output


def _load_request(path: str | Path) -> tuple[ProductRequest, bytes]:
    """Translate one authored product request through existing strict construction contracts."""
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Product requests must use external 'schema' fields.")
    if mapping.get("schema") != "hop.product-request/v1":
        raise ValueError(f"Unsupported HOP product request schema: {mapping.get('schema')!r}.")
    request = ProductRequest.model_validate_json(json.dumps(mapping))
    request.construction_source()  # Validate every expanded contract before exposing a preview.
    return request, canonical_json_bytes(mapping)


def prepare_construction_request(
    path: str | Path, *, compare_to: str | Path | None = None
) -> PreparedConstructionRequest:
    """Translate and preview one request, optionally compared with an explicit reference."""
    request, authored = _load_request(path)
    reference = None if compare_to is None else _load_request(compare_to)
    preview, preview_text = preview_product_request(request, authored, reference)
    return PreparedConstructionRequest._create(
        authored,
        canonical_json_bytes(request.construction_source()),
        render_product_request(request) + preview_text,
        preview,
    )
