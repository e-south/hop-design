"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/provisioning.py

Merges exact enzyme-provisioning policies across complete construction routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.payload import _content_id
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
    characterized_enzyme_digest,
)
from hop_design.models.reactions import ReactionProgram


def _catalog_entries(
    policies: tuple[EnzymeProvisioningPolicy, ...],
) -> tuple[CharacterizedEnzyme, ...]:
    entries: dict[str, CharacterizedEnzyme] = {}
    for policy in policies:
        for enzyme in policy.catalog.enzymes:
            previous = entries.setdefault(enzyme.enzyme_id, enzyme)
            if previous != enzyme:
                raise ValueError("Complete route cannot merge conflicting enzyme definitions.")
    return tuple(entries[key] for key in sorted(entries))


def merge_provisioning_policies(
    policies: tuple[EnzymeProvisioningPolicy, ...],
) -> EnzymeProvisioningPolicy:
    """Merge exact local policies without weakening restrictions or limits."""
    enzymes = _catalog_entries(policies)
    restrictions: dict[EnzymeRole, EnzymeRoleRestriction] = {}
    for policy in policies:
        for restriction in policy.role_restrictions:
            previous = restrictions.setdefault(restriction.role, restriction)
            if previous != restriction:
                raise ValueError("Complete route cannot merge conflicting role restrictions.")
    limits = tuple(policy.max_operations for policy in policies)
    return EnzymeProvisioningPolicy(
        catalog=CharacterizedEnzymeCatalog(
            catalog_id=_content_id(
                "enzyme-catalog",
                1,
                tuple(item.model_dump(mode="json") for item in enzymes),
            ),
            enzymes=enzymes,
        ),
        allowed_enzyme_ids=tuple(
            sorted(
                {
                    enzyme_id
                    for policy in policies
                    for enzyme_id in (
                        policy.allowed_enzyme_ids
                        or tuple(item.enzyme_id for item in policy.catalog.enzymes)
                    )
                }
            )
        ),
        forbidden_enzyme_ids=tuple(
            sorted({item for policy in policies for item in policy.forbidden_enzyme_ids})
        ),
        reserved_enzyme_ids=tuple(
            sorted({item for policy in policies for item in policy.reserved_enzyme_ids})
        ),
        max_operations=(
            None
            if any(item is None for item in limits)
            else sum(item for item in limits if item is not None)
        ),
        role_restrictions=tuple(restrictions[key] for key in sorted(restrictions)),
    )


def resolve_program_enzyme_definitions(
    *,
    program: ReactionProgram,
    policies: tuple[EnzymeProvisioningPolicy, ...],
) -> tuple[CharacterizedEnzyme, ...]:
    """Resolve every program enzyme against compatible molecular definitions."""
    definitions: dict[str, CharacterizedEnzyme] = {}
    digests: dict[str, str] = {}
    for policy in policies:
        for enzyme in policy.catalog.enzymes:
            digest = characterized_enzyme_digest(enzyme)
            previous = digests.setdefault(enzyme.enzyme_id, digest)
            if previous != digest:
                raise ValueError("A reaction program cannot use conflicting enzyme definitions.")
            definitions.setdefault(enzyme.enzyme_id, enzyme)
    required_ids = {
        operation.enzyme_id for stage in program.stages for operation in stage.operations
    }
    missing = required_ids - definitions.keys()
    if missing:
        raise ValueError(
            f"Reaction program references enzymes without definitions: {sorted(missing)}"
        )
    return tuple(definitions[enzyme_id] for enzyme_id in sorted(required_ids))


__all__ = ["merge_provisioning_policies", "resolve_program_enzyme_definitions"]
