"""Continue one explicitly bounded request through the existing molecular authorities."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

from hop_design.export.construction.request_execution import (
    render_complete_outcome,
    render_local_stop,
)
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction.source_partition.policy import SacrificialFragmentPolicy
from hop_design.serialization import canonical_json_bytes

from .complete.bundle import ConstructionCompilation
from .design_authority import compile_design_from_local_realizations
from .execution.cleanup import compile_request_candidate
from .execution.context import LocalSelection, describe_request_context, validate_design_id
from .execution.coverage import describe_local_coverage, describe_local_stop
from .execution.outcome import describe_complete_outcome
from .local_choices import list_local_realizations
from .local_public import discover_local_neighborhood
from .product_request import prepare_construction_request
from .public import (
    project_construction_trajectory,
)


@dataclass(frozen=True, init=False, repr=False)
class ConstructionRequestExecution:
    """Immutable delivery containing existing authorities and a non-authoritative summary."""

    _files: tuple[tuple[str, bytes], ...]
    _summary: bytes
    _report: str
    _compilation: ConstructionCompilation | None

    @classmethod
    def _capture(
        cls,
        directory: Path,
        summary: dict[str, object],
        report: str,
        *,
        compilation: ConstructionCompilation | None = None,
    ) -> Self:
        summary_bytes = canonical_json_bytes(summary)
        (directory / "summary.json").write_bytes(summary_bytes)
        (directory / "report.md").write_text(report, encoding="utf-8")
        instance = object.__new__(cls)
        object.__setattr__(instance, "_summary", summary_bytes)
        object.__setattr__(instance, "_report", report)
        object.__setattr__(instance, "_compilation", compilation)
        object.__setattr__(
            instance,
            "_files",
            tuple(
                (path.relative_to(directory).as_posix(), path.read_bytes())
                for path in sorted(directory.rglob("*"))
                if path.is_file()
            ),
        )
        return instance

    @property
    def json_bytes(self) -> bytes:
        """Read the derived outcome; molecular authority stays in the contained bundles."""
        return self._summary

    @property
    def report_text(self) -> str:
        return self._report

    def write(self, destination: str | Path) -> Path:
        """Publish a complete success or failure handoff, without replacing existing paths."""
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing execution path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            for relative, content in self._files:
                path = staging / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output


def _compile_selected_request(
    directory: Path,
    *,
    design_id: str,
    source: dict[str, Any],
    component: dict[str, str] | None,
    selection: LocalSelection,
    summary: dict[str, object],
    context: str,
) -> ConstructionRequestExecution:
    design = compile_design_from_local_realizations(
        design_id=design_id,
        payload_sequence=source["foldback"]["payload"]["payload"]["sequence"],
        endpoint=source["composition"]["endpoint"],
        hairpin_basal_arms=(
            None if component is None else (component["left_arm"], component["right_arm"])
        ),
        **selection,
    )
    design.write(directory / "design")
    authored = json.loads((directory / "inputs/request.json").read_bytes())
    cleanup = authored.get("source_cleanup")
    complete = compile_request_candidate(
        directory / "inputs/construction.json",
        design_bundle_path=directory / "design",
        selection=selection,
        cleanup=None if cleanup is None else SacrificialFragmentPolicy.model_validate(cleanup),
    )
    complete.write(directory / "construction")
    # The atomic write admits its staged bytes. Project the immutable compilation
    # already owned by this invocation; independently opened bundles still replay.
    outcome = describe_complete_outcome(complete)
    summary.update(outcome)
    rejections = outcome["rejection_reasons"]
    preparation_constraints = outcome["preparation_constraints"]
    scaffold_mismatches = outcome.get("scaffold_mismatches", [])
    if len(complete.materialized_realization_ids) == 1:
        project_construction_trajectory(
            complete, materialized_realization_id=complete.materialized_realization_ids[0]
        ).write(directory / "handoff")
    report = context + render_complete_outcome(
        status=complete.status,
        accepted=len(complete.materialized_realization_ids),
        rejections=rejections,
        preparation_constraints=preparation_constraints,
        scaffold_mismatches=scaffold_mismatches,
        actionable_sites=outcome.get("actionable_site_conflicts", []),
    )
    return ConstructionRequestExecution._capture(directory, summary, report, compilation=complete)


def execute_construction_request(
    path: str | Path,
    *,
    design_id: str,
    continuation: Literal["sole-witness"],
) -> ConstructionRequestExecution:
    """Continue only when each bounded local search returns exactly one witness.

    This opt-in policy makes no optimality or exhaustive-route claim. All search
    budgets, end requirements, and material permissions remain authored inputs.
    """
    if continuation != "sole-witness":
        raise ValueError("Continuation must be explicitly 'sole-witness'.")
    validate_design_id(design_id)
    prepared = prepare_construction_request(path)
    source, component, summary, context = describe_request_context(
        prepared, continuation=continuation
    )
    coverage = summary["local_coverage"]
    assert isinstance(coverage, dict)
    with tempfile.TemporaryDirectory(prefix="hop-request-") as temporary:
        directory = Path(temporary)
        prepared.write(directory / "inputs")
        locals_by_family = {}
        for family in ("foldback", "basal"):
            if source[family] is None:
                continue
            local = discover_local_neighborhood(directory / "inputs" / f"{family}.json")
            local.write(directory / family)
            coverage[family] = describe_local_coverage(local, family)
            local_rejections = coverage[family]["rejection_counts"]
            stop = describe_local_stop(coverage[family], family)
            if stop is not None:
                summary.update(stop)
                return ConstructionRequestExecution._capture(
                    directory,
                    summary,
                    context
                    + render_local_stop(
                        family=family,
                        count=local.realization_count,
                        status=stop["status"],
                        termination=local.termination_reason,
                        rejections=local_rejections,
                    ),
                )
            locals_by_family[family] = local
        foldback = locals_by_family["foldback"]
        selection: LocalSelection = {
            "foldback": foldback,
            "foldback_realization_id": list_local_realizations(foldback)[0].realization_id,
        }
        if "basal" in locals_by_family:
            basal = locals_by_family["basal"]
            selection["basal"] = basal
            selection["basal_realization_id"] = list_local_realizations(basal)[0].realization_id
        return _compile_selected_request(
            directory,
            design_id=design_id,
            source=source,
            component=component,
            selection=selection,
            summary=summary,
            context=context,
        )
