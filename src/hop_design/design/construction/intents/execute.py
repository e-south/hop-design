"""Resolve once, evaluate explicitly, and admit existing survey choices without a second engine."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from hop_design.export.publication import (
    publish_directory_create_only,
    publish_directory_files_create_only,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.variants.applicability import inapplicable_reason
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.serialization import canonical_json_bytes

from ..execution.feedback import DiscoveryFeedback, ProgressObserver, StopRequest
from ..options.order import validate_options_objective
from ..packets.capture import capture_packet
from ..surveys.branches import SurveyBranches
from ..surveys.choices import load_interface_survey_choices
from ..surveys.public import evaluate_interface_survey
from .base import DesignChoices
from .resolve import ResolvedDesignRequest, resolve_design_request
from .results import InsertDesignChoices

_DEFAULT_EFFORT = SurveyEvaluationLimits(
    scheduling="discovery", local_nodes=1000, local_realizations=1000, release_site_pairs=1000
)


def discover_designs(
    request: str | Path | dict[str, Any],
    destination: str | Path,
    *,
    max_evaluations: int = 64,
    effort: dict[str, Any] | None = None,
    first_choices: int | None = None,
    objective: dict[str, Any] | None = None,
    on_progress: ProgressObserver | None = None,
    should_stop: StopRequest | None = None,
) -> DesignChoices:
    """Discover complete preparations from optional intent in a new portable directory.

    End words are not required. Execution limits affect how much is examined,
    never which molecular designs are permitted. Both endpoint owners can
    continue explicitly; hairpins optionally stop at a first-choice count.
    """
    _batch_size(max_evaluations)
    _first_choices(first_choices)
    DiscoveryFeedback(on_progress, should_stop)
    limits = (
        _DEFAULT_EFFORT
        if effort is None
        else SurveyEvaluationLimits.model_validate_json(canonical_json_bytes(effort))
    )
    if objective is not None:
        if limits.objective is not None:
            raise ValueError("Declare the search objective once, outside or inside effort.")
        limits = limits.model_copy(
            update={
                "objective": DesignSearchObjective.model_validate_json(
                    canonical_json_bytes(objective)
                )
            }
        )
    resolved = resolve_design_request(request)
    if json.loads(resolved.json_bytes).get("schema") == "hop.design-family-preview/v1":
        if on_progress is not None or should_stop is not None:
            raise ValueError(
                "Family feedback requires member-aware execution; use exact-member discovery."
            )
        from ..sequence_families.design.execute import start_family

        return start_family(
            resolved,
            destination,
            max_evaluations=max_evaluations,
            effort=effort,
            first_choices=first_choices,
            objective=objective,
        )
    limits = _validate_execution(
        resolved, limits, first_choices=first_choices, default_effort=effort is None
    )
    files = {"intent/" + name: data for name, data in resolved._files}
    files["effort.json"] = canonical_json_bytes(limits)
    output = Path(destination)
    if resolved._roots:
        publish_directory_files_create_only(files, output, protected_root=resolved._roots)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            for name, data in files.items():
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return continue_design_discovery(
        output,
        max_evaluations=max_evaluations,
        first_choices=first_choices,
        on_progress=on_progress,
        should_stop=should_stop,
    )


def _validate_execution(
    resolved: ResolvedDesignRequest,
    limits: SurveyEvaluationLimits,
    *,
    first_choices: int | None,
    default_effort: bool,
) -> SurveyEvaluationLimits:
    product = json.loads(resolved.json_bytes)["intent"]["product"]
    if limits.objective is not None:
        for key in limits.objective.parameters:
            reason = inapplicable_reason(parameter_definition(key), product)
            if reason:
                raise ValueError(f"Diversity parameter {key!r} is not applicable: {reason}")
        if product == "released_insert":
            native = InterfaceSurveyRequest.model_validate_json(
                dict(resolved._files)["request.json"]
            )
            SurveyBranches(native).search_order(limits)
        else:
            validate_options_objective(
                ProductRequest.model_validate_json(dict(resolved._files)["request.json"]),
                limits.objective,
            )
    if (
        first_choices is not None
        and json.loads(resolved.json_bytes)["intent"]["product"] == "released_insert"
    ):
        raise ValueError("First-choice stopping is currently supported for hairpin endpoints.")
    if default_effort and json.loads(resolved.json_bytes)["intent"]["product"] != "released_insert":
        limits = limits.model_copy(update={"local_realizations": 64})
    return limits


def _batch_size(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("max_evaluations must be a positive integer.")


def _first_choices(value: int | None) -> None:
    if value is not None and (type(value) is not int or value < 1):
        raise ValueError("first_choices must be a positive integer or None.")


def _admit_resolution(directory: Path) -> bytes:
    _, files = capture_packet(directory / "intent", schema="hop.resolved-design-request-packet/v1")
    original = json.loads(files["intent.json"])
    authored = dict(original)
    # The captured context is portable, even if its original user file has moved.
    authored["context"] = json.loads(files["context.json"])
    if authored.get("prefer_preparation") is not None:
        from .preference import PREFERENCE_DIRECTORY, PREFERENCE_SELECTION

        portable = {"bundle_path": PREFERENCE_DIRECTORY, "selection_path": PREFERENCE_SELECTION}
        if authored["prefer_preparation"] != portable:
            raise ValueError("Saved preparation preference must use its captured authority.")
        authored["prefer_preparation"] = {
            key: str(directory / "intent" / value) for key, value in portable.items()
        }
    rebuilt = json.loads(resolve_design_request(authored).json_bytes)
    stored = json.loads(files["summary.json"])
    rebuilt["intent"] = original
    origin = stored.get("context", {}).get("origin")
    if origin not in {"user", "packaged"}:
        raise ValueError("Saved context origin disagrees with the public contract.")
    if origin == "packaged" and original.get("context") not in (None, rebuilt["context"]["id"]):
        raise ValueError("Saved packaged context and authored intention disagree.")
    rebuilt["context"]["origin"] = origin
    if (
        canonical_json_bytes(rebuilt["effective_request"]) != files["request.json"]
        or stored != rebuilt
    ):
        raise ValueError("Saved design intention, permissions and effective request disagree.")
    if (directory / "revision").exists():
        from .revision import load_design_revision

        revised = json.loads(load_design_revision(directory / "revision").json_bytes)["request"]
        if revised != original:
            raise ValueError("Discovery intent disagrees with its saved permission revision.")
    return files["summary.json"]


def continue_design_discovery(
    directory: str | Path,
    *,
    max_evaluations: int = 64,
    first_choices: int | None = None,
    on_progress: ProgressObserver | None = None,
    should_stop: StopRequest | None = None,
) -> DesignChoices:
    """Explicitly evaluate more of the same request and return its new result snapshot."""
    _batch_size(max_evaluations)
    _first_choices(first_choices)
    feedback = DiscoveryFeedback(on_progress, should_stop)
    root = Path(directory).resolve(strict=True)
    if (root / "family").exists():
        if on_progress is not None or should_stop is not None:
            raise ValueError(
                "Family feedback requires member-aware execution; use exact-member discovery."
            )
        from ..sequence_families.design.execute import continue_family

        return continue_family(root, max_evaluations=max_evaluations, first_choices=first_choices)
    resolution_bytes = _admit_resolution(root)
    resolution = json.loads(resolution_bytes)
    if resolution["intent"]["product"] != "released_insert":
        from .hairpins import evaluate_hairpins

        return evaluate_hairpins(
            root,
            max_evaluations,
            resolution=resolution_bytes,
            first_choices=first_choices,
            **(
                {"feedback": feedback} if on_progress is not None or should_stop is not None else {}
            ),
        )
    limits = SurveyEvaluationLimits.model_validate_json((root / "effort.json").read_bytes())
    if first_choices is not None:
        raise ValueError("First-choice stopping is currently supported for hairpin endpoints.")
    index = root / "survey.sqlite"
    progress = evaluate_interface_survey(
        root / "intent/request.json",
        index,
        max_evaluations=max_evaluations,
        resume=index.exists(),
        on_progress=on_progress,
        should_stop=should_stop,
        **limits.model_dump(mode="json"),
    )
    reason = progress["termination_reason"]
    if reason not in {"evaluation_budget", "exhausted_enumeration", "cancelled"}:
        raise ValueError(
            f"Discovery stopped: {reason}; {progress['new_evaluations']} additional "
            "evaluations committed. Saved choices remain available through "
            "load_design_choices or design query. Unfinished targets remain unresolved. "
            "Review execution resources before continuing; repeating unchanged can "
            "stop at the same limit."
        )
    return load_design_choices(root)


def load_design_choices(directory: str | Path) -> DesignChoices:
    """Admit an existing discovery once; repeated queries reuse its immutable pool."""
    root = Path(directory).resolve(strict=True)
    if (root / "family").exists():
        from ..sequence_families.design.choices import load_family

        return load_family(root)
    resolution = _admit_resolution(root)
    if json.loads(resolution)["intent"]["product"] != "released_insert":
        from .hairpins import load_hairpin_choices

        return load_hairpin_choices(root, resolution)
    pool = load_interface_survey_choices(root / "intent/request.json", root / "survey.sqlite")
    result = object.__new__(InsertDesignChoices)
    object.__setattr__(result, "_directory", root)
    object.__setattr__(result, "_resolution", resolution)
    object.__setattr__(result, "_pool", pool)
    return result
