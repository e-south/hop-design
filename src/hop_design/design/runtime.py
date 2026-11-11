"""Identify the executing producer without exporting machine-local locations."""

from __future__ import annotations

import json
import os
import platform
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from importlib.metadata import distribution, version
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from hop_design.serialization import canonical_json_bytes, sha256_digest


def _source_fingerprints(package: Path) -> dict[str, str]:
    """Hash every source on every call; avoid repeated Path parsing for each file."""
    base = os.fspath(package)
    files = {}
    for directory, folders, names in os.walk(base):
        prefix = directory[len(base) + 1 :].replace(os.sep, "/")
        for name in (*folders, *names):
            if name.endswith(".py"):
                relative = f"{prefix}/{name}" if prefix else name
                with open(os.path.join(directory, name), "rb") as source:
                    files[relative] = sha256_digest(source.read())
    return files


def producer_identity() -> dict[str, str]:
    """Bind source, authority-bearing compatibility policy and runtime versions."""
    package = Path(__file__).resolve().parents[1]
    files = _source_fingerprints(package)
    code = sha256_digest(canonical_json_bytes(files))
    policy = "assets/checkpoint-compatibility.json"
    files[policy] = sha256_digest((package / policy).read_bytes())
    return {
        "package_version": version("hop-design"),
        "package_content": sha256_digest(canonical_json_bytes(files)),
        "package_code": code,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        **{name: version(name) for name in ("pydantic", "pydantic-core", "PyYAML", "typer")},
    }


def runtime_identity() -> dict[str, object]:
    """Report declared installation provenance separately from actual package content."""
    identity = producer_identity()
    raw = distribution("hop-design").read_text("direct_url.json")
    direct = json.loads(raw) if raw else {}
    source: dict[str, object] = {"kind": "unrecorded"}
    if isinstance(direct, dict) and isinstance(direct.get("url"), str):
        url = urlsplit(direct["url"])
        if url.scheme == "file":
            source = {"kind": "local"}
        elif url.scheme == "https" and url.hostname and url.username is None:
            public_url = urlunsplit((url.scheme, url.netloc, url.path, "", ""))
            vcs = direct.get("vcs_info", {})
            archive = direct.get("archive_info", {})
            if isinstance(vcs, dict) and vcs.get("vcs") == "git":
                source = {"kind": "git", "url": public_url, "commit": vcs.get("commit_id")}
            elif isinstance(archive, dict):
                source = {"kind": "archive", "url": public_url, "hashes": archive.get("hashes", {})}
    return {
        "schema": "hop/runtime-identity/v1",
        "distribution": "hop-design",
        "version": identity.pop("package_version"),
        **identity,
        "source": source,
        "report_schemas": [
            "hop/design-report/v1",
            "hop/local-result-report/v1",
            "hop/local-batch-report/v1",
            "hop/source-partition-report/v1",
            "hop/local-choices-report/v1",
            "hop/basal-panel-report/v1",
            "hop/construction-report/v1",
            "hop/linear-source-method-report/v1",
        ],
    }


_creator: ContextVar[str | None] = ContextVar("authority_creator_version", default=None)
_admitted: ContextVar[frozenset[str] | None] = ContextVar(
    "admitted_authority_creators", default=None
)


def creation_version() -> str:
    """Tag new authorities with this installation, or replay with their creator.

    This affects serialized creation metadata only. Executing runtime identity
    and survey producer admission always use the actual installation.
    """
    declared = _creator.get()
    return version("hop-design") if declared is None else declared


@contextmanager
def replay_creation(creator: str) -> Iterator[None]:
    """Replay under a creator admitted by the caller's checkpoint boundary.

    Readers still recompute every scientific field and require canonical-byte
    equality. Readers must not take this value from the result being checked.
    This private context neither accepts checkpoint producers nor
    changes package version, dependency identity or compatibility policy.
    """
    if type(creator) is not str or not creator.strip():
        raise ValueError("Authority creator version must be a nonempty string.")
    token = _creator.set(creator)
    try:
        yield
    finally:
        _creator.reset(token)


@contextmanager
def admitted_creators(creators: tuple[str, ...]) -> Iterator[None]:
    """Scope nested replay to an already-admitted checkpoint's creator history.

    This private scope does not authorize a producer transition. Its caller
    must first verify the stored history and its supported compatibility rules.
    """
    if not creators or any(type(value) is not str or not value.strip() for value in creators):
        raise ValueError("Admitted creators must contain nonempty versions.")
    token = _admitted.set(frozenset(creators))
    try:
        yield
    finally:
        _admitted.reset(token)


@contextmanager
def replay_authority(creator: str) -> Iterator[None]:
    """Replay a child authority only within an admitted creator history.

    Ordinary readers retain their exact expected creator. A label in an
    unadmitted result cannot enable historical replay by itself.
    """
    allowed = _admitted.get()
    if allowed is None:
        yield
    elif creator not in allowed:
        raise ValueError("Child authority creator is absent from the admitted checkpoint history.")
    else:
        with replay_creation(creator):
            yield
