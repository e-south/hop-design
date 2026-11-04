"""Resolve a verified reference into ordinary broad-request candidate coordinates."""

from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.foldback.solutions import FoldbackSequenceSolution
from hop_design.models.construction.complete.evaluation_inputs import replay_linear_source_embedding
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.complete.result import ConstructionSpaceResult
from hop_design.models.construction.payload import SourceOrientation
from hop_design.models.construction.projections.materials import external_material_uses
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits

from ..branches import SurveyBranches
from ..coordinates import coordinate_rank, interleaved_rank
from ..partitions import PartitionPlans
from .geometry import target_and_geometries
from .materials import auxiliary_materials_match, require_source_materials
from .source import basal_source_slice, source_context_rank
from .types import PreferenceOutOfScope, PreparationAddress, material_signature


def addresses_for_preparation(
    *,
    result: ConstructionSpaceResult,
    preparation: MaterializedConstructionRealization,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    partitions: PartitionPlans,
) -> tuple[PreparationAddress, ...]:
    """Find candidate addresses, without granting a witness or changing permissions.

    The caller supplies a verified result/selection. Every returned address still
    requires ordinary complete compilation and exact external-material comparison.
    Local membership includes oriented programs and endpoint-conditioned joint
    source/adapter correlations. Only finite geometry/program lists are visited.
    """
    target, geometries = target_and_geometries(result, preparation, branches)
    require_source_materials(preparation, branches)
    basal, foldback = preparation.basal_authority, preparation.foldback_authority
    assert basal is not None
    source = preparation.source_preparation
    top, bottom = source.product_state.molecules
    prefix, _, _ = replay_linear_source_embedding(
        foldback=foldback, source_sequence=top.sequence, complement_sequence=bottom.sequence
    )
    source_frame = prefix + foldback.payload_sequence
    materials = material_signature(preparation)
    adapter = next(
        material
        for material, use in external_material_uses(preparation)
        if use.role.value == "ligation_adapter"
    )
    payload_segment = foldback.payload_source_map.segments[0]
    foldback_solution = FoldbackSequenceSolution(
        source_reference_sequence=foldback.source_reference_sequence,
        retained_sequence=foldback.retained_sequence,
        loop_sequence=foldback.loop_sequence,
        foldback_arm_sequence=foldback.foldback_arm_sequence,
        junction_boundary=(
            payload_segment.source_span.end.offset
            if payload_segment.orientation is SourceOrientation.FORWARD
            else payload_segment.source_span.start.offset
        ),
        terminus_boundary=foldback.terminus.boundary.offset,
        enzyme_bindings=foldback.enzyme_bindings,
    )
    nick = next(b for b in basal.enzyme_bindings if b.binding_id == basal.basal_nick.binding_id)
    answers = set()
    for geometry in geometries:
        product = branches.product(target, branch=geometry, limits=limits)
        parts = partitions.get(product)
        if parts.empty_candidates or parts.conflict is not None:
            continue
        assert parts.foldback is not None and parts.basal_candidates is not None
        try:
            foldback_ranks = parts.foldback.ranks_of(
                foldback_solution, program_kind=foldback.program_kind
            )
        except ValueError:
            continue
        population = parts.basal_candidates
        for program_index, support in enumerate(population.supports):
            domain = support.index.domain
            if (
                domain.program.nick_enzyme.enzyme_id != nick.enzyme_id
                or domain.program.nick_orientation != nick.orientation
                or domain.target.nick_strand != basal.basal_nick.strand
                or domain.program.future_release_action != basal.future_release_action
            ):
                continue
            try:
                local_source, context = basal_source_slice(
                    domain=domain,
                    source=source_frame,
                    payload_start=len(prefix),
                    payload_end=len(source_frame),
                )
                context_rank = source_context_rank(
                    branches.request.materialization.source_preparation.source_ssdna, context
                )
                adapter_length = len(domain.base_domains) - domain.adapter_span.start.offset
                member = domain.materialize(local_source, adapter.sequence_5prime[:adapter_length])
                if isinstance(member, BasalPlacementFailure):
                    continue
                local_rank = support.rank_of(member)
            except ValueError:
                continue
            basal_rank = interleaved_rank(
                population.program_cardinalities, program_index, local_rank
            )
            # Context can affect endpoint admission. Re-resolve its ordinary page
            # rather than assuming an address from the representative context fits.
            exact = branches.product(
                target, branch=context_rank * branches.geometry_count + geometry, limits=limits
            )
            exact_parts = partitions.get(exact)
            if not auxiliary_materials_match(
                product=exact, domain=domain, member=member, prefix=prefix, reference=preparation
            ):
                continue
            if exact_parts != parts:
                if exact_parts.empty_candidates or exact_parts.conflict is not None:
                    continue
                exact_population = exact_parts.basal_candidates
                assert exact_population is not None
                matching = [
                    (i, s)
                    for i, s in enumerate(exact_population.supports)
                    if s.index.domain == domain
                ]
                if len(matching) != 1:
                    continue
                i, admitted = matching[0]
                try:
                    basal_rank = interleaved_rank(
                        exact_population.program_cardinalities, i, admitted.rank_of(member)
                    )
                except ValueError:
                    continue
            for foldback_rank in foldback_ranks:
                assert exact_parts.foldback is not None and exact_parts.basal_candidates is not None
                page = coordinate_rank(
                    (exact_parts.foldback.parts, exact_parts.basal_candidates.parts),
                    (foldback_rank, basal_rank),
                )
                answers.add(
                    PreparationAddress(target, geometry, page, context_rank, context, materials)
                )
    if not answers:
        raise PreferenceOutOfScope(
            "Reference has no admitted oriented source/adapter member and auxiliary context "
            "inside the declared geometry and endpoint constraints."
        )
    return tuple(sorted(answers))
