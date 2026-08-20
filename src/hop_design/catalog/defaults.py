"""Versioned, visible defaults for the generic non-retron demonstration."""

from __future__ import annotations

from hop_design.models.coordinates import BasePairCount, Boundary, Span
from hop_design.models.junction import (
    BasalJunction,
    FoldbackJunction,
    JunctionPairKind,
    JunctionPairObservation,
)
from hop_design.models.processing import DirectSynthesisStep, ProcessingRoute

DEFAULTS_REF = "hop:defaults/generic-direct-synthesis@1"
FOLDBACK_REF = "hop:foldback-junction/generic-gtttc@1"
BASAL_REF = "hop:basal-junction/generic-g-c@1"
PROCESSING_ROUTE_REF = "hop:processing-route/generic-direct-synthesis@1"
CONSTRAINT_PROFILE_REF = "hop:constraint-profile/generic-cloneable@1"
CATALOG_REF = "hop:catalog/generic-demonstration@1"


def generic_direct_synthesis_route() -> ProcessingRoute:
    """Return the immutable, synthetic route shipped for public demonstrations."""
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
    return ProcessingRoute(
        route_id=PROCESSING_ROUTE_REF,
        kind="direct_synthesis",
        description=(
            "Synthetic direct-synthesis route for software demonstration only; "
            "it is not a laboratory protocol or application profile."
        ),
        catalog_ref=CATALOG_REF,
        foldback_junction=foldback,
        basal_junction=basal,
        steps=(DirectSynthesisStep(step_id="direct-synthesis"),),
    )
