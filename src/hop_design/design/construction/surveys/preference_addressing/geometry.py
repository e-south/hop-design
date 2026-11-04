"""Match declared structural coordinates and operative enzyme definitions."""

from itertools import product

from hop_design.models.construction.complete.clone.geometry import clone_payload_end_offsets
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.complete.result import ConstructionSpaceResult
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.surveys.targets import FOUR_BASE_WORDS
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget
from hop_design.models.enzymes import characterized_enzyme_digest

from ..branches import SurveyBranches
from ..coordinates import coordinate_rank
from .types import PreferenceOutOfScope


def target_and_geometries(
    result: ConstructionSpaceResult,
    route: MaterializedConstructionRealization,
    branches: SurveyBranches,
) -> tuple[int, tuple[int, ...]]:
    request = branches.request
    if route not in result.realizations:
        raise PreferenceOutOfScope("Selected preparation is absent from its reference result.")
    if (
        route.final_product.reference.endpoint is not ConstructionEndpoint.CLONE_READY_DUPLEX
        or route.basal_authority is None
        or result.request.release is None
    ):
        raise PreferenceOutOfScope("Interface preferences require a complete released insert.")
    if route.foldback_authority.payload_sequence != request.stem_arm:
        raise PreferenceOutOfScope("Reference payload differs from the invariant supplied stem.")
    ends = {end.product_end: end for end in route.final_product.cohesive_ends}
    for side in ("left", "right"):
        authored, frame = getattr(result.request.release, side), getattr(request.interfaces, side)
        if (
            authored.orientation != frame.orientation
            or ends[side].overhang_end != frame.overhang_end
        ):
            raise PreferenceOutOfScope(
                "Reference receiving-interface orientation is not permitted."
            )
    try:
        target = (request.targets.left_words or FOUR_BASE_WORDS).index(
            ends["left"].sequence
        ) * request.targets.right_count + (request.targets.right_words or FOUR_BASE_WORDS).index(
            ends["right"].sequence
        )
    except ValueError as exc:
        raise PreferenceOutOfScope(
            "Reference sticky ends are outside the requested word domain."
        ) from exc
    basal, foldback = route.basal_authority, route.foldback_authority
    action = basal.future_release_action
    if action is None:
        raise PreferenceOutOfScope("Reference has no exact basal release program.")
    _same_definitions(result, route, branches)
    gaps = clone_payload_end_offsets(
        ends=(ends["left"], ends["right"]),
        encoding_start=route.final_product.design_projection.source_span.start.offset,
        payload_boundaries=route.design.payload_boundaries,
    )
    achieved = foldback.local_realization.achieved_geometry
    basal_geometry = basal.local_realization.achieved_geometry
    assert isinstance(achieved, FoldbackTarget) and isinstance(basal_geometry, BasalTarget)
    dimensions = (
        tuple(i for i, p in enumerate(branches.placements) if (p.left_bp, p.right_bp) == gaps),
        tuple(
            i
            for i, n in enumerate(request.basal.geometry.nick_offsets_nt)
            if n == basal_geometry.nick_offset_nt
        ),
        tuple(range(len(request.basal.annealing_lengths_nt))),
        tuple(i for i, method in enumerate(branches.release_methods) if method == action.enzyme_id),
        tuple(
            i
            for i, case in enumerate(branches.foldback_cases)
            if all(
                getattr(case, key) == getattr(achieved, key)
                for key in (
                    "nick_strand",
                    "junction_offset_nt",
                    "loop_length_nt",
                    "annealing_arm_length_bp",
                )
            )
            and case.loop_sequence in (None, foldback.loop_sequence)
        ),
        tuple(
            i
            for i, p in enumerate(request.release.basal_projections)
            if p.product_end == action.requirement.product_end
            and p.recognition_material == action.requirement.recognition_material
        ),
    )
    ranks = tuple(
        sorted(coordinate_rank(branches.geometry_sizes, tuple(c)) for c in product(*dimensions))
    )
    if not ranks:
        raise PreferenceOutOfScope(
            "Reference geometry or release method is outside the declared envelope."
        )
    return target, ranks


def _same_definitions(
    result: ConstructionSpaceResult,
    route: MaterializedConstructionRealization,
    branches: SurveyBranches,
) -> None:
    assert result.basal_authority is not None and route.basal_authority is not None
    catalogs = (
        (
            result.foldback_authority.neighborhood.request.enzyme_provisioning.catalog,
            route.foldback_authority.enzyme_bindings,
        ),
        (
            result.basal_authority.discovery.request.enzyme_provisioning.catalog,
            route.basal_authority.enzyme_bindings,
        ),
    )
    for catalog, bindings in catalogs:
        for binding in bindings:
            try:
                expected = catalog.by_id(binding.enzyme_id)
                actual = branches.request.enzyme_catalog.by_id(binding.enzyme_id)
            except KeyError as exc:
                raise PreferenceOutOfScope(
                    "Reference enzyme is absent from the survey catalog."
                ) from exc
            if characterized_enzyme_digest(expected) != characterized_enzyme_digest(actual):
                raise PreferenceOutOfScope(
                    "Reference enzyme definition differs from the survey catalog."
                )
