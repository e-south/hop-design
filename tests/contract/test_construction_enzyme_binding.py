"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_enzyme_binding.py

Tests exact construction-enzyme placement replay and cohesive-end derivation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError

from hop_design.models.construction.enzyme_binding import (
    ConstructionEnzymeBinding,
    derive_cohesive_end,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation
from tests.contract.test_basal_construction_discovery import _nickase, _type_iis


def _span(length: int) -> Span:
    return Span(start=Boundary(offset=0), end=Boundary(offset=length))


def test_enzyme_binding_replays_forward_and_reverse_nickase_placements() -> None:
    enzyme = _nickase()
    forward = ConstructionEnzymeBinding.create(
        enzyme_id=enzyme.enzyme_id,
        role=EnzymeRole.BASAL_NICK,
        strand=Strand.TOP,
        recognition_span=_span(3),
        orientation=SiteOrientation.FORWARD,
        reference_cut=Boundary(offset=2),
        complement_cut=None,
    )
    reverse = ConstructionEnzymeBinding.create(
        enzyme_id=enzyme.enzyme_id,
        role=EnzymeRole.BASAL_NICK,
        strand=Strand.BOTTOM,
        recognition_span=_span(3),
        orientation=SiteOrientation.REVERSE,
        reference_cut=None,
        complement_cut=Boundary(offset=1),
    )

    forward.assert_definition_replay(enzyme=enzyme, sequence="AAC")
    reverse.assert_definition_replay(enzyme=enzyme, sequence="GTT")
    assert forward.binding_id != reverse.binding_id


def test_enzyme_binding_rejects_definition_role_site_and_cut_drift() -> None:
    nickase = _nickase()
    restriction = _type_iis()
    nick_binding = ConstructionEnzymeBinding.create(
        enzyme_id=nickase.enzyme_id,
        role=EnzymeRole.BASAL_NICK,
        strand=Strand.TOP,
        recognition_span=_span(3),
        orientation=SiteOrientation.FORWARD,
        reference_cut=Boundary(offset=2),
        complement_cut=None,
    )
    basal_restriction = ConstructionEnzymeBinding.create(
        enzyme_id=restriction.enzyme_id,
        role=EnzymeRole.BASAL_NICK,
        strand=Strand.TOP,
        recognition_span=_span(6),
        orientation=SiteOrientation.FORWARD,
        reference_cut=Boundary(offset=6),
        complement_cut=Boundary(offset=10),
    )
    end_nickase = ConstructionEnzymeBinding.create(
        enzyme_id=nickase.enzyme_id,
        role=EnzymeRole.END_GENERATION,
        strand=None,
        recognition_span=_span(3),
        orientation=SiteOrientation.FORWARD,
        reference_cut=Boundary(offset=2),
        complement_cut=Boundary(offset=3),
    )

    with pytest.raises(ValueError, match="embedded enzyme definition"):
        nick_binding.assert_definition_replay(enzyme=restriction, sequence="AAC")
    with pytest.raises(ValueError, match="characterized nickase"):
        basal_restriction.assert_definition_replay(
            enzyme=restriction,
            sequence=restriction.recognition_pattern,
        )
    with pytest.raises(ValueError, match="duplex restriction enzyme"):
        end_nickase.assert_definition_replay(enzyme=nickase, sequence="AAC")
    with pytest.raises(ValueError, match="recognition"):
        nick_binding.assert_definition_replay(enzyme=nickase, sequence="CCC")
    with pytest.raises(ValueError, match="cuts"):
        nick_binding.model_copy(
            update={"reference_cut": Boundary(offset=1)}
        ).assert_definition_replay(
            enzyme=nickase,
            sequence="AAC",
        )


def test_enzyme_binding_requires_role_specific_exact_cuts() -> None:
    with pytest.raises(ValidationError, match="controlled strand"):
        ConstructionEnzymeBinding.create(
            enzyme_id="example:enzyme/nick@1",
            role=EnzymeRole.BASAL_NICK,
            strand=Strand.TOP,
            recognition_span=_span(3),
            orientation=SiteOrientation.FORWARD,
            reference_cut=None,
            complement_cut=Boundary(offset=1),
        )
    with pytest.raises(ValidationError, match="two exact strand cuts"):
        ConstructionEnzymeBinding.create(
            enzyme_id="example:enzyme/restriction@1",
            role=EnzymeRole.END_GENERATION,
            strand=None,
            recognition_span=_span(6),
            orientation=SiteOrientation.FORWARD,
            reference_cut=Boundary(offset=2),
            complement_cut=None,
        )


@pytest.mark.parametrize(
    ("reference_cut", "complement_cut", "side", "strand_id", "polarity", "sequence"),
    (
        (2, 6, "left", "top", StrandEnd.FIVE_PRIME, "GTCC"),
        (2, 6, "right", "bottom", StrandEnd.FIVE_PRIME, "GGAC"),
        (6, 2, "left", "bottom", StrandEnd.THREE_PRIME, "GGAC"),
        (6, 2, "right", "top", StrandEnd.THREE_PRIME, "GTCC"),
    ),
)
def test_cohesive_end_derivation_preserves_cut_order_and_product_side(
    reference_cut: int,
    complement_cut: int,
    side: Literal["left", "right"],
    strand_id: str,
    polarity: StrandEnd,
    sequence: str,
) -> None:
    binding = ConstructionEnzymeBinding.create(
        enzyme_id="example:enzyme/end@1",
        role=EnzymeRole.END_GENERATION,
        strand=None,
        recognition_span=_span(8),
        orientation=SiteOrientation.FORWARD,
        reference_cut=Boundary(offset=reference_cut),
        complement_cut=Boundary(offset=complement_cut),
    )

    end = derive_cohesive_end(
        side=side,
        top_sequence="AAGTCCTA",
        binding=binding,
        primary_strand_id="top",
        complementary_strand_id="bottom",
    )

    assert end.protruding_strand_id == strand_id
    assert end.overhang_end is polarity
    assert end.sequence == sequence


@pytest.mark.parametrize(
    ("reference_cut", "complement_cut"),
    ((None, 2), (2, None), (2, 2)),
)
def test_cohesive_end_rejects_missing_or_blunt_cut_geometry(
    reference_cut: int | None,
    complement_cut: int | None,
) -> None:
    binding = ConstructionEnzymeBinding.create(
        enzyme_id="example:enzyme/end@1",
        role=EnzymeRole.FOLDBACK_NICK,
        strand=None,
        recognition_span=_span(8),
        orientation=SiteOrientation.FORWARD,
        reference_cut=(None if reference_cut is None else Boundary(offset=reference_cut)),
        complement_cut=(None if complement_cut is None else Boundary(offset=complement_cut)),
    )

    with pytest.raises(ValueError, match="cohesive-end-unavailable"):
        derive_cohesive_end(
            side="left",
            top_sequence="AAGTCCTA",
            binding=binding,
            primary_strand_id="top",
            complementary_strand_id="bottom",
        )
