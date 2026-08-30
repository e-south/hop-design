"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/source_documents/__init__.py

Loads bounded JSON and YAML mapping documents from safe local files.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import errno
import json
import os
import stat
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode
from yaml.resolver import BaseResolver
from yaml.tokens import AliasToken, AnchorToken

DEFAULT_SOURCE_MAX_BYTES = 1_000_000


class SourceDocumentLimitError(ValueError):
    """Raised before decoding when a source document exceeds its byte limit."""

    def __init__(self, *, actual: int, max_bytes: int) -> None:
        self.actual = actual
        self.max_bytes = max_bytes
        super().__init__(f"HOP source max_bytes exceeded: {actual} > {max_bytes}.")


class _StrictSourceLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous mapping documents."""


def _unique_json_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"HOP source contains duplicate mapping key: {key!r}.")
        mapping[key] = value
    return mapping


def _unique_yaml_mapping(
    loader: _StrictSourceLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[object, Any]:
    mapping: dict[object, Any] = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ValueError("HOP source YAML aliases, anchors, or merge keys are not supported.")
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("HOP source YAML mapping keys must be strings.")
        if key in mapping:
            raise ValueError(f"HOP source contains duplicate mapping key: {key!r}.")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictSourceLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _unique_yaml_mapping,
)


def _read_source_bytes(
    source: Path,
    *,
    max_bytes: int,
    source_label: str,
) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(source, flags)
    except OSError as error:
        if error.errno == errno.ELOOP or source.is_symlink():
            raise ValueError(f"{source_label} source must not be a symlink.") from error
        raise ValueError(f"{source_label} source is not a regular file: {source}.") from error
    try:
        opened = os.fstat(descriptor)
        try:
            named = os.lstat(source)
        except OSError as error:
            raise ValueError(
                f"{source_label} source changed while it was being opened: {source}."
            ) from error
        if not stat.S_ISREG(opened.st_mode) or not stat.S_ISREG(named.st_mode):
            raise ValueError(f"{source_label} source is not a regular file: {source}.")
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            raise ValueError(f"{source_label} source changed while it was being opened: {source}.")
        if opened.st_size > max_bytes:
            raise SourceDocumentLimitError(actual=opened.st_size, max_bytes=max_bytes)
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise SourceDocumentLimitError(actual=len(content), max_bytes=max_bytes)
        after_read = os.fstat(descriptor)
        if (
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != (
            after_read.st_size,
            after_read.st_mtime_ns,
            after_read.st_ctime_ns,
        ):
            raise ValueError(f"{source_label} source changed while it was being read: {source}.")
        return content
    finally:
        os.close(descriptor)


def load_source_mapping(
    path: str | Path,
    *,
    max_bytes: int = DEFAULT_SOURCE_MAX_BYTES,
    source_label: str = "HOP",
) -> dict[str, Any]:
    """Load one bounded JSON or YAML document whose root is a mapping."""
    source = Path(path)
    suffix = source.suffix.lower()
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    text = _read_source_bytes(
        source,
        max_bytes=max_bytes,
        source_label=source_label,
    ).decode("utf-8")
    payload: Any
    if suffix == ".json":
        payload = json.loads(text, object_pairs_hook=_unique_json_mapping)
    elif suffix in {".yaml", ".yml"}:
        if any(isinstance(token, AliasToken | AnchorToken) for token in yaml.scan(text)):
            raise ValueError("HOP source YAML aliases, anchors, or merge keys are not supported.")
        payload = yaml.load(text, Loader=_StrictSourceLoader)
    else:
        raise ValueError(f"{source_label} file extension must be .json, .yaml, or .yml.")
    if not isinstance(payload, dict):
        raise ValueError(f"{source_label} document root must be a mapping.")
    return payload


__all__ = [
    "DEFAULT_SOURCE_MAX_BYTES",
    "SourceDocumentLimitError",
    "load_source_mapping",
]
