"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/space/authority.py

Normalizes substrate-space molecular rules and seals design-set authority.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from itertools import product
from typing import Literal

from hop_design.catalog.defaults import DEFAULTS_REF
from hop_design.kernel.bundle_identity import design_set_id, manifest_digest_for_design_set
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.design_space import (
    HairpinDesignMember,
    HairpinDesignSet,
    SubstrateSpaceSpec,
    VariableAssignment,
)
from hop_design.models.sequence import iupac_bases
from hop_design.models.space.scientist import DesignSetClaimStatus, MolecularSubstrateSpace
from hop_design.serialization import canonical_json_bytes, sha256_digest

CANONICAL_DNA_ORDER: tuple[Literal["A", "C", "G", "T"], ...] = ("A", "C", "G", "T")


def molecular_space(spec: SubstrateSpaceSpec) -> MolecularSubstrateSpace:
    """Project authored rules into their normalized molecular authority."""
    payload_domains: list[tuple[Literal["A", "C", "G", "T"], ...]] = []
    for segment in spec.payload:
        sequence = segment.fixed or segment.variable or ""
        for symbol in sequence:
            bases = iupac_bases(symbol)
            payload_domains.append(tuple(base for base in CANONICAL_DNA_ORDER if base in bases))
    return MolecularSubstrateSpace(
        payload_domains=tuple(payload_domains),
        defaults_ref=DEFAULTS_REF,
    )


def assignment_text(
    spec: SubstrateSpaceSpec,
    assignments: tuple[VariableAssignment, ...],
) -> str:
    """Describe one exact assignment using authored segment labels where available."""
    assignments_by_position = {assignment.position: assignment.base for assignment in assignments}
    labels: list[str] = []
    cursor = 1
    for segment in spec.payload:
        sequence = segment.fixed or segment.variable or ""
        segment_positions = tuple(range(cursor, cursor + len(sequence)))
        cursor += len(sequence)
        if segment.variable is None:
            continue
        assigned = tuple(
            (position, assignments_by_position[position])
            for position in segment_positions
            if position in assignments_by_position
        )
        if not assigned:
            continue
        if segment.label is not None:
            labels.append(f"{segment.label}={''.join(base for _, base in assigned)}")
        else:
            labels.extend(f"{position}={base}" for position, base in assigned)
    return "; ".join(labels) or "fixed payload"


def exact_payloads(
    space: MolecularSubstrateSpace,
) -> tuple[tuple[tuple[VariableAssignment, ...], str], ...]:
    """Expand one normalized molecular space in canonical assignment order."""
    variable_positions = tuple(
        position
        for position, domain in enumerate(space.payload_domains, start=1)
        if len(domain) > 1
    )
    variable_domains = tuple(domain for domain in space.payload_domains if len(domain) > 1)
    template = [domain[0] for domain in space.payload_domains]
    results: list[tuple[tuple[VariableAssignment, ...], str]] = []
    for bases in product(*variable_domains):
        exact = template.copy()
        assignments = tuple(
            VariableAssignment(position=position, base=base)
            for position, base in zip(variable_positions, bases, strict=True)
        )
        for assignment in assignments:
            exact[assignment.position - 1] = assignment.base
        results.append((assignments, "".join(exact)))
    return tuple(results)


def member_design_id(*, spec_digest: str, assignments: tuple[VariableAssignment, ...]) -> str:
    """Derive a stable member identifier from molecular space and assignment."""
    assignment_digest = sha256_digest(
        canonical_json_bytes([assignment.model_dump(mode="json") for assignment in assignments])
    )
    return (
        f"space-{spec_digest.removeprefix('sha256:')[:12]}-"
        f"member-{assignment_digest.removeprefix('sha256:')[:12]}"
    )


def provisional_design_set(
    *,
    spec: SubstrateSpaceSpec,
    spec_digest: str,
    members: tuple[HairpinDesignMember, ...],
    artifacts: tuple[ArtifactManifestEntry, ...],
) -> HairpinDesignSet:
    """Build the complete manifest content before content identity is sealed."""
    unique_designs = sum(member.disposition == "canonical" for member in members)
    duplicate_count = len(members) - unique_designs
    return HairpinDesignSet(
        design_set_id="hop:design-set/pending/pending",
        spec_digest=spec_digest,
        defaults_ref=DEFAULTS_REF,
        theoretical_cardinality=len(members),
        enumerated_assignments=len(members),
        unique_designs=unique_designs,
        duplicate_count=duplicate_count,
        claim_status=DesignSetClaimStatus.model_validate(
            {
                "space_accounting": {
                    "status": "complete",
                    "basis": "all_declared_assignments_enumerated",
                },
                "digital_design": {
                    "status": "verified",
                    "basis": "all_unique_member_authorities_replay_verified",
                },
                "named_method": {"status": "not_evaluated"},
                "destination_compatibility": {"status": "not_evaluated"},
                "physical_construction": {"status": "not_recorded"},
                "quality_control": {"status": "not_recorded"},
                "biological_activity": {"status": "not_recorded"},
            }
        ),
        members=members,
        artifacts=artifacts,
        manifest_digest=f"sha256:{'0' * 64}",
    )


def seal_design_set(design_set: HairpinDesignSet) -> HairpinDesignSet:
    """Seal one complete design-set manifest with its content identity."""
    digest = manifest_digest_for_design_set(design_set)
    return design_set.model_copy(
        update={
            "design_set_id": design_set_id(manifest_digest=digest),
            "manifest_digest": digest,
        }
    )
