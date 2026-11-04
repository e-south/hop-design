"""Group verified physical products separately from their manufacturing histories."""

from typing import Any

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.projections.materials import external_oligos
from hop_design.models.molecular_state import CohesiveEnd, MolecularStrand, StrandPairObservation
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..public import ConstructionCompilation, VerifiedConstructionBundle

MOLECULAR_SIGNATURE_SCHEMA = "hop.molecular-signature/v2"


def _contact_key(pair: StrandPairObservation, strands: dict[str, int]) -> list[Any]:
    """A contact is an undirected edge in oriented nucleotide coordinates."""
    left, right = sorted(
        (
            (strands[pair.left_strand_id], pair.left_index, pair.left_base),
            (strands[pair.right_strand_id], pair.right_index, pair.right_base),
        )
    )
    return [left[0], left[1], right[0], right[1], left[2], right[2], pair.kind.value]


def molecular_signature(
    strands: tuple[MolecularStrand, ...],
    pairings: tuple[StrandPairObservation, ...],
    ends: tuple[CohesiveEnd, ...],
    *,
    topology: str,
) -> dict[str, Any]:
    """Use oriented product coordinates, not strand names or precursor cut coordinates.

    Each recorded strand is a continuous covalent chain. Historical join origins
    do not change that chain's physical identity. Pairing and end orientation do.
    The product's primary/return strand ordering remains explicit; no rotational
    or strand-permutation equivalence is inferred.
    """
    indices = {strand.strand_id: i for i, strand in enumerate(strands)}
    return {
        "schema": MOLECULAR_SIGNATURE_SCHEMA,
        "topology": topology,
        "strands": [
            {
                "sequence": strand.sequence,
                "five_prime_end": strand.five_prime_end.value,
                "three_prime_end": strand.three_prime_end.value,
            }
            for strand in strands
        ],
        "pairings": sorted(_contact_key(pair, indices) for pair in pairings),
        "interfaces": sorted(
            [
                {
                    "product_end": end.product_end,
                    "protruding_strand": indices[end.protruding_strand_id],
                    "overhang_end": end.overhang_end.value,
                    "sequence": end.sequence,
                }
                for end in ends
            ],
            key=lambda item: item["product_end"],
        ),
    }


def molecular_identities(
    receipt: ConstructionCompilation | VerifiedConstructionBundle, identity: str
) -> dict[str, str]:
    route = next(
        r
        for r in receipt._verified_source().result.realizations
        if r.materialized_realization_id == identity
    )
    hairpin = describe_hairpin(route)
    hairpin_graph = molecular_signature(
        hairpin.state.molecules, hairpin.state.pairings, (), topology="single_stranded_hairpin"
    )
    product = route.final_product
    endpoint_graph = (
        hairpin_graph
        if product.reference.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
        else molecular_signature(
            product.strands,
            product.pairings,
            product.cohesive_ends,
            topology=product.reference.topology,
        )
    )
    return {
        stage: sha256_digest(canonical_json_bytes(graph))
        for stage, graph in (("hairpin", hairpin_graph), ("endpoint", endpoint_graph))
    }


def stage_groups(options: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped = {}
    for stage in ("hairpin", "endpoint"):
        members: dict[str, list[str]] = {}
        for option in options:
            members.setdefault(option["molecular_identity"][stage], []).append(option["label"])
        grouped[stage] = [
            {"molecule_id": identity, "stage": stage, "option_labels": labels}
            for identity, labels in members.items()
        ]
    return grouped


def preparation_materials(
    receipt: ConstructionCompilation | VerifiedConstructionBundle, identity: str
) -> dict[str, Any]:
    route = next(
        r
        for r in receipt._verified_source().result.realizations
        if r.materialized_realization_id == identity
    )
    return route_materials(route)


def route_materials(route: MaterializedConstructionRealization) -> dict[str, Any]:
    """Role identities from the external oligos of one complete molecular record."""
    return {
        use.role.value: {
            "material_id": material.material_id,
            "length_nt": len(material.sequence_5prime),
        }
        for material, uses in external_oligos(route)
        for use in uses
    }
