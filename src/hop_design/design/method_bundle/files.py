"""Named linear-source method operations over existing portable JSON authorities."""

from __future__ import annotations

import json
from pathlib import Path

from hop_design.design.linear_source_method import compile_linear_source_multinick_hairpin_pcr
from hop_design.design.source_documents import load_source_mapping
from hop_design.models.bundle import MethodBundle
from hop_design.models.linear_source_method import (
    LinearSourceMultinickHairpinPcrRequest,
    LinearSourceMultinickHairpinPcrResult,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .authority import (
    compile_linear_source_method_bundle,
    load_verified_method_bundle,
)


def _request(path: Path) -> LinearSourceMultinickHairpinPcrRequest:
    if path.suffix.lower() != ".json":
        raise ValueError("Method request file extension must be .json.")
    mapping = load_source_mapping(path, source_label="HOP method request")
    return LinearSourceMultinickHairpinPcrRequest.model_validate_json(json.dumps(mapping))


def _report(
    request: LinearSourceMultinickHairpinPcrRequest,
    result: LinearSourceMultinickHairpinPcrResult,
    bundle: MethodBundle | None = None,
) -> str:
    return json.dumps(
        {
            "schema": "hop/linear-source-method-report/v1",
            "verification": "deterministic_derivation",
            "request": request.model_dump(mode="json", by_alias=True),
            "request_sha256": sha256_digest(canonical_json_bytes(request)),
            "result": result.model_dump(mode="json", by_alias=True),
            "result_sha256": sha256_digest(canonical_json_bytes(result)),
            "bundle": bundle.model_dump(mode="json", by_alias=True) if bundle else None,
            "bundle_file_sha256": sha256_digest(canonical_json_bytes(bundle)) if bundle else None,
        },
        sort_keys=True,
    )


def resolve_linear_source_method_file(source: Path) -> str:
    """Resolve an exact request, including expected infeasible outcomes, without publication."""
    request = _request(source)
    return _report(request, compile_linear_source_multinick_hairpin_pcr(request))


def compile_linear_source_method_file(source: Path, output: Path) -> str:
    """Publish a complete method bundle and return its canonical authority report."""
    compiled = compile_linear_source_method_bundle(_request(source))
    compiled.write(output)
    return _report(compiled.request, compiled.result, compiled.bundle)


def verify_linear_source_method_file(source: Path) -> str:
    """Replay a retained method bundle and report the independently derived outcome."""
    verified = load_verified_method_bundle(source)
    result = compile_linear_source_multinick_hairpin_pcr(verified.request)
    return _report(verified.request, result, verified.bundle)
