"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/surveys/storage/compatibility.py

Admits exact package transitions without changing molecular computation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from importlib.resources import files

from hop_design.models.construction.surveys.compatibility import SurveyCompatibilityPolicy
from hop_design.serialization import canonical_json_bytes, sha256_digest

_IDENTITY_FIELDS = {"package_version", "package_content", "package_code"}


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate survey compatibility field.")
        result[key] = value
    return result


def _policy_bytes() -> bytes:
    return files("hop_design").joinpath("assets/checkpoint-compatibility.json").read_bytes()


def authorize_transition(source: dict[str, str], target: dict[str, str]) -> str:
    """Require a shipped exact-code declaration and identical non-package inputs.

    Policy bytes enter the actual producer fingerprint. The declaration binds
    target Python code separately so its own bytes cannot create a hash cycle.
    Callers cannot supply a policy or waive a missing declaration.
    """
    raw = _policy_bytes()
    try:
        if not 0 < len(raw) <= 1_048_576:
            raise ValueError("Survey compatibility declaration exceeds its size limit.")
        json.loads(raw, object_pairs_hook=_unique_fields)
        policy = SurveyCompatibilityPolicy.model_validate_json(raw)
        same_runtime = {k: v for k, v in source.items() if k not in _IDENTITY_FIELDS} == {
            k: v for k, v in target.items() if k not in _IDENTITY_FIELDS
        }
        for entry in policy.declarations:
            if (
                same_runtime
                and entry.source_version == source.get("package_version")
                and entry.source_content == source.get("package_content")
                and entry.target_version == target.get("package_version")
                and entry.target_code == target.get("package_code")
            ):
                return sha256_digest(canonical_json_bytes(entry))
    except ValueError as error:
        raise ValueError("Invalid survey compatibility declaration.") from error
    raise ValueError("No supported survey compatibility declaration for these producers.")
