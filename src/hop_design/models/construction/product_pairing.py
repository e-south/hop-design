"""Explicit end-relative pairing permissions; coordinate derivation stays in release models."""

from typing import Literal

from hop_design.models.base import HopModel

from .targets import BasalPairAllowance, BasalPairConstraint


class ProductConstraintConflict(ValueError):
    """A scoped molecular contradiction, distinct from malformed input or a defect."""

    def __init__(self, message: str, *, code: str, position_from_ligation: int):
        super().__init__(message)
        self.code = code
        self.position_from_ligation = position_from_ligation

    def diagnostic(self) -> dict[str, str | int]:
        return {
            "code": self.code,
            "message": str(self),
            "position_from_ligation": self.position_from_ligation,
            "scope": "declared_product_branch",
        }


def _intersect_classes(
    first: BasalPairAllowance,
    second: BasalPairAllowance,
    *,
    position: int,
    code: str = "end_pairing_permission_conflict",
) -> BasalPairAllowance:
    if first is BasalPairAllowance.ANY:
        return second
    if second is BasalPairAllowance.ANY or first is second:
        return first
    raise ProductConstraintConflict(
        f"Pairing permission {first.value} conflicts with {second.value} at position {position}.",
        code=code,
        position_from_ligation=position,
    )


def require_proximal_match(
    contacts: tuple[BasalPairConstraint, ...],
) -> tuple[BasalPairConstraint, ...]:
    """Intersect product permissions with the PCR-bearing route's ligation requirement."""
    return tuple(
        contact.model_copy(
            update={
                "allowed_class": _intersect_classes(
                    contact.allowed_class,
                    BasalPairAllowance.MATCH,
                    position=0,
                    code="required_proximal_match_conflict",
                )
            }
        )
        if contact.position_from_ligation == 0
        else contact
        for contact in contacts
    )


class EndFootprintPairing(HopModel):
    """Declare matching proximal pairs and one permission across the source end footprint."""

    reference: Literal["left_end_source_contacts"]
    proximal: Literal["match"]
    within: BasalPairAllowance

    def expand(
        self,
        footprint: tuple[tuple[int, str], ...],
        absolute: tuple[BasalPairConstraint, ...],
    ) -> tuple[BasalPairConstraint, ...]:
        # The caller establishes the source coordinate frame. An empty overlap
        # then grants no noncanonical contacts; proximal matching still applies.
        positions = {position for position, _ in footprint}
        last_position = max(positions, default=0)
        if last_position >= 100_000:
            raise ValueError("End-footprint pairing may expand to at most 100000 positions.")
        generated = {
            position: BasalPairConstraint(
                position_from_ligation=position,
                allowed_class=self.within if position in positions else BasalPairAllowance.MATCH,
            )
            for position in range(last_position + 1)
        }
        seen: set[int] = set()
        for contact in absolute:
            position = contact.position_from_ligation
            if position in seen:
                raise ValueError(f"Duplicate absolute pairing declaration at position {position}.")
            seen.add(position)
            if position in generated:
                contact = contact.model_copy(
                    update={
                        "allowed_class": _intersect_classes(
                            generated[position].allowed_class,
                            contact.allowed_class,
                            position=position,
                        )
                    }
                )
            # An authored base restriction stays authoritative, including outside the footprint.
            generated[position] = contact
        return tuple(generated[position] for position in sorted(generated))
