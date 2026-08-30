"""Versioned, visible defaults for the generic hairpin demonstration."""

from __future__ import annotations

from hop_design.models.coordinates import BasePairCount, Boundary, Span
from hop_design.models.derivation import CatalogJunctionDerivation
from hop_design.models.junction import (
    BasalJunction,
    FoldbackJunction,
    JunctionPairKind,
    JunctionPairObservation,
)

DEFAULTS_REF = "hop:defaults/generic-hairpin-design@2"
FOLDBACK_REF = "hop:foldback-junction/generic-gtttc@1"
BASAL_REF = "hop:basal-junction/generic-g-c@1"
DESIGN_DERIVATION_REF = "hop:design-derivation/generic-catalog-junctions@1"
CONSTRAINT_PROFILE_REF = "hop:constraint-profile/generic-hairpin@2"
CATALOG_REF = "hop:catalog/generic-demonstration@1"
DEFAULTS_DISPLAY_NAME = "Generic GTTTC hairpin context"
DEFAULTS_ANATOMY_SUMMARY = (
    "GTTTC foldback junction (TTT turn) with a one-base-pair G:C basal junction."
)


def generic_catalog_junction_derivation() -> CatalogJunctionDerivation:
    """Return the immutable catalog junctions used by the public example."""
    foldback = FoldbackJunction(
        junction_id=FOLDBACK_REF,
        sequence="GTTTC",
        retained_tract_span=Span(start=Boundary(offset=0), end=Boundary(offset=1)),
        turn_span=Span(start=Boundary(offset=1), end=Boundary(offset=4)),
        foldback_arm_span=Span(start=Boundary(offset=4), end=Boundary(offset=5)),
        pairs=(
            JunctionPairObservation(
                left_index=0,
                right_index=4,
                left_base="G",
                right_base="C",
                kind=JunctionPairKind.WATSON_CRICK,
            ),
        ),
    )
    basal = BasalJunction(
        junction_id=BASAL_REF,
        left_arm="G",
        right_arm="C",
        pair_count=BasePairCount(value=1),
        pairs=(
            JunctionPairObservation(
                left_index=0,
                right_index=0,
                left_base="G",
                right_base="C",
                kind=JunctionPairKind.WATSON_CRICK,
            ),
        ),
    )
    return CatalogJunctionDerivation(
        derivation_id=DESIGN_DERIVATION_REF,
        description=(
            "Synthetic catalog junctions for software demonstration only; "
            "they make no production-method or application claim."
        ),
        catalog_ref=CATALOG_REF,
        foldback_junction=foldback,
        basal_junction=basal,
    )
