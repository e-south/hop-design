"""Pure route semantics and strand complement helpers."""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.strand_state import StrandExposureRoute


@dataclass(frozen=True)
class StrandRouteSemantics:
    """Literal strand roles implied by one exposure route."""

    active_strand: Strand
    retained_partner_strand: Strand
    nicked_strand: Strand


def route_semantics(route: StrandExposureRoute) -> StrandRouteSemantics:
    """Return the three coupled strand roles for one route."""
    if route is StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK:
        return StrandRouteSemantics(
            active_strand=Strand.BOTTOM,
            retained_partner_strand=Strand.TOP,
            nicked_strand=Strand.TOP,
        )
    return StrandRouteSemantics(
        active_strand=Strand.TOP,
        retained_partner_strand=Strand.BOTTOM,
        nicked_strand=Strand.BOTTOM,
    )


def complement_iupac(sequence: str) -> str:
    """Complement a strand without reversing its coordinate direction."""
    return reverse_complement_iupac(sequence)[::-1]


__all__ = ["StrandRouteSemantics", "complement_iupac", "route_semantics"]
