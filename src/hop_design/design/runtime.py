"""Identify the executing producer without exporting machine-local locations."""

from __future__ import annotations

import json
import platform
from importlib.metadata import distribution, version
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from hop_design.serialization import canonical_json_bytes, sha256_digest


def producer_identity() -> dict[str, str]:
    """Bind producer Python source bytes and runtime dependency versions."""
    package = Path(__file__).resolve().parents[1]
    files = {
        path.relative_to(package).as_posix(): sha256_digest(path.read_bytes())
        for path in sorted(package.rglob("*.py"))
    }
    return {
        "package_version": version("hop-design"),
        "package_content": sha256_digest(canonical_json_bytes(files)),
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
