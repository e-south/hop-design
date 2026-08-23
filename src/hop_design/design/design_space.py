"""Bounded, deterministic planning for composable resolved design axes."""

from __future__ import annotations

from itertools import product
from math import prod

from pydantic import BaseModel

from hop_design.design.basal import evaluate_basal_pairing
from hop_design.design.compile import check_spec
from hop_design.design.foldback import evaluate_foldback
from hop_design.models.design_space import (
    DesignSpacePlan,
    DesignSpaceRow,
    DuplicateDesignSequencePolicy,
    ResolvedDesignSpace,
)
from hop_design.models.spec import ResolvedHopSpec
from hop_design.serialization import canonical_json_bytes, sha256_digest


class DesignSpaceBudgetExceededError(ValueError):
    """Raised before row allocation when a Cartesian space exceeds its hard bound."""

    def __init__(self, *, cardinality: int, max_designs: int) -> None:
        self.cardinality = cardinality
        self.max_designs = max_designs
        super().__init__(
            f"Design-space cardinality {cardinality} exceeds max_designs {max_designs}."
        )


class DuplicateDesignSequenceError(ValueError):
    """Raised when two combinations project one sequence under fail policy."""

    def __init__(
        self,
        *,
        sequence: str,
        first_design_id: str,
        duplicate_design_id: str,
    ) -> None:
        self.sequence = sequence
        self.first_design_id = first_design_id
        self.duplicate_design_id = duplicate_design_id
        super().__init__(
            "Design-space combinations project a duplicate final sequence: "
            f"{first_design_id!r} and {duplicate_design_id!r}."
        )


def _design_id(
    space: ResolvedDesignSpace,
    *,
    payload_record_id: str,
    payload_sequence: str,
    foldback_option_id: str,
    foldback_request: BaseModel,
    basal_option_id: str,
    basal_request: BaseModel,
    release_option_id: str,
    release_request: BaseModel | None,
) -> str:
    seed = canonical_json_bytes(
        {
            "space_id": space.space_id,
            "payload_record_id": payload_record_id,
            "payload_sequence": payload_sequence,
            "foldback_option_id": foldback_option_id,
            "foldback_request": foldback_request.model_dump(mode="json", by_alias=True),
            "basal_option_id": basal_option_id,
            "basal_request": basal_request.model_dump(mode="json", by_alias=True),
            "release_option_id": release_option_id,
            "release_request": (
                None
                if release_request is None
                else release_request.model_dump(mode="json", by_alias=True)
            ),
        }
    )
    suffix = sha256_digest(seed).removeprefix("sha256:")[:12]
    return f"{space.space_id}-{suffix}"


def plan_design_space(space: ResolvedDesignSpace) -> DesignSpacePlan:
    """Check every bounded Cartesian combination without compiling bundle artifacts."""
    cardinality = prod(
        (
            len(space.payloads.records),
            len(space.foldbacks),
            len(space.basals),
            len(space.releases),
        )
    )
    if cardinality > space.limits.max_designs:
        raise DesignSpaceBudgetExceededError(
            cardinality=cardinality,
            max_designs=space.limits.max_designs,
        )

    rows: list[DesignSpaceRow] = []
    projected_sequences: dict[str, str] = {}
    duplicate_final_sequence_count = 0
    for payload, foldback, basal, release in product(
        space.payloads.records,
        space.foldbacks,
        space.basals,
        space.releases,
    ):
        spec = ResolvedHopSpec(
            design_id=_design_id(
                space,
                payload_record_id=payload.record_id,
                payload_sequence=payload.payload.sequence,
                foldback_option_id=foldback.option_id,
                foldback_request=foldback.request,
                basal_option_id=basal.option_id,
                basal_request=basal.request,
                release_option_id=release.option_id,
                release_request=release.request,
            ),
            payload=payload.payload,
            foldback=foldback.request,
            basal=basal.request,
            release=release.request,
            defaults_ref=space.defaults_ref,
            catalog_ref=space.catalog_ref,
            constraint_profile_ref=space.constraint_profile_ref,
            design_derivation_ref=space.design_derivation_ref,
            constraints=space.per_design_constraints,
            external_refs=space.external_refs,
        )
        report = check_spec(spec)
        projected_final_sequence: str | None = None
        if not report.has_errors:
            foldback_evaluation = evaluate_foldback(foldback.request)
            basal_evaluation = evaluate_basal_pairing(
                basal.request.pairing,
                constraints=basal.request.constraints,
            )
            projected_final_sequence = "".join(
                (
                    basal_evaluation.profile.left_arm,
                    payload.payload.sequence,
                    foldback_evaluation.junction_sequence,
                    payload.payload.paired_sequence,
                    basal_evaluation.profile.right_arm,
                )
            )
            first_design_id = projected_sequences.get(projected_final_sequence)
            if first_design_id is not None:
                if space.duplicate_final_sequence_policy is DuplicateDesignSequencePolicy.FAIL:
                    raise DuplicateDesignSequenceError(
                        sequence=projected_final_sequence,
                        first_design_id=first_design_id,
                        duplicate_design_id=spec.design_id,
                    )
                duplicate_final_sequence_count += 1
            else:
                projected_sequences[projected_final_sequence] = spec.design_id
        rows.append(
            DesignSpaceRow(
                payload_record_id=payload.record_id,
                foldback_option_id=foldback.option_id,
                basal_option_id=basal.option_id,
                release_option_id=release.option_id,
                spec=spec,
                report=report,
                projected_final_sequence=projected_final_sequence,
            )
        )
    feasible_count = sum(not row.report.has_errors for row in rows)
    return DesignSpacePlan(
        space_id=space.space_id,
        cardinality=cardinality,
        feasible_count=feasible_count,
        infeasible_count=cardinality - feasible_count,
        duplicate_final_sequence_count=duplicate_final_sequence_count,
        rows=tuple(rows),
    )


__all__ = [
    "DesignSpaceBudgetExceededError",
    "DuplicateDesignSequenceError",
    "plan_design_space",
]
