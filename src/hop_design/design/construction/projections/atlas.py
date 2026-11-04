"""Compose admitted molecular facts; no construction search or inferred reaction states."""

from itertools import pairwise

from hop_design.models.construction.complete.pcr.authority import (
    AdapterAnnealingAuthority,
    PrimerExtensionAuthority,
)
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.complete.transition import ConstructionTransitionKind
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.atlas import (
    AtlasMaterialInput,
    AtlasTransition,
    MolecularAtlas,
    MolecularScenes,
)
from hop_design.models.construction.projections.inspection import MolecularStateInspection
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.inspection import MolecularAddress

from .inspection import inspection_states, project_molecular_inspection
from .inspection_correspondence import inspection_correspondence
from .inspection_sites import RecognitionAncestry
from .overhead.complete import construction_cost


def project_teaching_scenes(
    route: MaterializedConstructionRealization, *, enzyme_names: dict[str, str] | None = None
) -> MolecularScenes:
    """Inspect the frames that locate teaching features, not every processing step.

    Source primer spans, association contacts, hairpin geometry and final interfaces
    require their recorded frames. Enzyme precursors supply planned cut boundaries.
    Recognition ancestry still follows the complete route, including omitted states.
    """
    state_ids = {
        route.source_preparation.product_state.state_id,
        describe_hairpin(route).state.state_id,
        route.construction_program.states[-1].state_id,
    }
    for transition in route.construction_program.transitions:
        if isinstance(transition.pcr_authority, AdapterAnnealingAuthority):
            state_ids.add(transition.post_state_id)
        if transition.kind in {
            ConstructionTransitionKind.ENZYME_PHASE,
            ConstructionTransitionKind.END_GENERATION,
        }:
            state_ids.add(transition.pre_state_id)
    return MolecularScenes(
        materialized_realization_id=route.materialized_realization_id,
        states=_state_inspections(route, None, enzyme_names, frozenset(state_ids)),
        inputs=tuple(i for i in project_material_inputs(route) if i.pre_state_id in state_ids),
        construction_cost=construction_cost(route),
    )


def _state_inspections(
    route: MolecularRouteView,
    focus: MolecularAddress | None,
    enzyme_names: dict[str, str] | None,
    state_ids: frozenset[str] | None = None,
) -> tuple[MolecularStateInspection, ...]:
    recognition_ancestry = RecognitionAncestry(route)
    return tuple(
        project_molecular_inspection(
            route,
            state.state_id,
            focus,
            enzyme_names=enzyme_names or {},
            recognition_ancestry=recognition_ancestry,
        )
        for state in inspection_states(route)
        if state_ids is None or state.state_id in state_ids
    )


def project_molecular_atlas(
    route: MaterializedConstructionRealization,
    focus: MolecularAddress | None = None,
    *,
    enzyme_names: dict[str, str] | None = None,
) -> MolecularAtlas:
    atlas = project_recorded_molecular_atlas(route, focus, enzyme_names=enzyme_names)
    return atlas.model_copy(update={"construction_cost": construction_cost(route)})


def project_recorded_molecular_atlas(
    route: MolecularRouteView,
    focus: MolecularAddress | None = None,
    *,
    enzyme_names: dict[str, str] | None = None,
) -> MolecularAtlas:
    """Portray verified records without re-admitting them to the current compiler.

    The caller owns producing-version verification. This function preserves exact
    states, bindings and identities; it neither searches nor invents missing
    endpoint evidence. Compiler-derived cost is deliberately absent.
    """
    states = inspection_states(route)
    source = route.source_preparation
    inputs = project_material_inputs(route)
    transitions = [
        AtlasTransition(
            authority_id=source.authority_id,
            kind="source_copying",
            correspondence=inspection_correspondence(route, states[0], route, states[1]),
        )
    ]
    transitions.extend(
        AtlasTransition(
            authority_id=t.transition_id,
            kind=t.kind.value,
            correspondence=inspection_correspondence(route, a, route, b),
        )
        for t, (a, b) in zip(
            route.construction_program.transitions, pairwise(states[1:]), strict=True
        )
    )
    return MolecularAtlas(
        materialized_realization_id=route.materialized_realization_id,
        states=_state_inspections(route, focus, enzyme_names),
        transitions=tuple(transitions),
        inputs=tuple(inputs),
    )


def project_material_inputs(route: MolecularRouteView) -> tuple[AtlasMaterialInput, ...]:
    states = inspection_states(route)
    source = route.source_preparation
    inputs = []
    authorities = [source] + [
        t.pcr_authority
        for t in route.construction_program.transitions
        if isinstance(t.pcr_authority, PrimerExtensionAuthority)
    ]
    for authority in authorities:
        original = next(s for s in states if s.state_id == authority.pre_state_id).molecules[0]
        for primer, use in (
            (authority.forward_primer, authority.forward_primer_use),
            (authority.reverse_primer, authority.reverse_primer_use),
        ):
            binding = next(b for b in authority.bindings if b.primer_id == use.use_id)
            # Forward source copying binds the recorded complementary product;
            # it is a binding annotation, not an invented annealed intermediate.
            template = next(
                (
                    s
                    for s in states
                    if s.state_id in (authority.pre_state_id, authority.post_state_id)
                    and any(m.strand_id == binding.template_strand_id for m in s.molecules)
                ),
                None,
            )
            reference: tuple[MolecularAddress, ...] = ()
            if binding.template_strand_id != original.strand_id:
                n = len(original.sequence)
                reference = tuple(
                    MolecularAddress(
                        state_id=authority.pre_state_id,
                        strand_id=original.strand_id,
                        index=n - 1 - i,
                    )
                    for i in reversed(
                        range(binding.template_span.start.offset, binding.template_span.end.offset)
                    )
                )
            inputs.append(
                AtlasMaterialInput(
                    authority_id=authority.authority_id,
                    pre_state_id=authority.pre_state_id,
                    post_state_id=authority.post_state_id,
                    material=primer.oligo,
                    material_use=use,
                    binding=binding,
                    binding_state_id=template.state_id if template else None,
                    binding_context="recorded_state" if template else "derived_template",
                    annealing_length_nt=primer.annealing_length_nt,
                    introduction_reference=reference,
                )
            )
    for transition in route.construction_program.transitions:
        adapter = transition.pcr_authority
        if isinstance(adapter, AdapterAnnealingAuthority):
            inputs.append(
                AtlasMaterialInput(
                    authority_id=adapter.authority_id,
                    pre_state_id=adapter.pre_state_id,
                    post_state_id=adapter.post_state_id,
                    material=adapter.adapter,
                    material_use=adapter.adapter_use,
                    binding_context="not_applicable",
                )
            )
    return tuple(inputs)
