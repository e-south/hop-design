"""Check reference orders through existing source and auxiliary policy resolution."""

from hop_design.kernel.construction.basal.domains import BasalSequenceDomain
from hop_design.kernel.construction.basal.programs import BasalSequenceSolution
from hop_design.models.construction.complete.auxiliary.resolution import (
    resolve_endpoint_auxiliaries,
)
from hop_design.models.construction.complete.basal_embedding import basal_nick_boundary
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.complete.source_preparation.resolution import (
    resolve_source_duplex_preparation,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.projections.materials import external_material_uses
from hop_design.models.sequence import reverse_complement_iupac

from ...basal.realization import _realization
from ..branches import SurveyBranches
from .types import PreferenceOutOfScope


def require_source_materials(
    route: MaterializedConstructionRealization, branches: SurveyBranches
) -> None:
    source = route.source_preparation
    top, bottom = source.product_state.molecules
    try:
        derived = resolve_source_duplex_preparation(
            policy=branches.request.materialization.source_preparation,
            source_sequence=source.source_ssdna.sequence_5prime,
            payload_source_span=source.payload_source_span,
            reference_five_prime_end=top.five_prime_end,
            complement_five_prime_end=bottom.five_prime_end,
        )
    except ValueError as exc:
        raise PreferenceOutOfScope(
            "Reference source materials do not satisfy the survey policies."
        ) from exc
    if any(
        getattr(derived, key) != getattr(source, key)
        for key in ("source_ssdna", "forward_primer", "reverse_primer")
    ):
        raise PreferenceOutOfScope("Survey source policies resolve different external materials.")


def auxiliary_materials_match(
    *,
    product: ProductRequest,
    domain: BasalSequenceDomain,
    member: BasalSequenceSolution,
    prefix: str,
    reference: MaterializedConstructionRealization,
) -> bool:
    """Resolve only this exact basal member, not any surrounding population."""
    local = product.construction_source().basal
    assert local is not None
    basal = _realization(
        request=local,
        payload_sequence=domain.payload_sequence,
        target=domain.target,
        route=domain.program,
        solution=member,
    )
    if isinstance(basal, str):
        return False
    retained = prefix[basal_nick_boundary(basal, prefix) :]
    policy = product.materialization.endpoint_auxiliaries
    assert policy is not None
    try:
        resolved = resolve_endpoint_auxiliaries(
            policy=policy,
            basal=basal,
            pcr_core_sequence=prefix
            + reference.foldback_authority.retained_sequence
            + (reverse_complement_iupac(retained) if retained else ""),
            source_primer_region_length_nt=len(prefix),
        )
    except ValueError:
        return False
    expected = {use.role.value: material for material, use in external_material_uses(reference)}
    return all(
        expected[role] == material
        for role, material in (
            ("ligation_adapter", resolved.adapter),
            ("endpoint_forward_primer", resolved.forward_primer.oligo),
            ("endpoint_reverse_primer", resolved.reverse_primer.oligo),
        )
    )
