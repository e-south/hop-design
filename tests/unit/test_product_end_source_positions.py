"""Map an oriented end requirement onto the source side of a basal contact window."""

import pytest

from hop_design.models.construction.basal_release import BasalFutureReleaseRequirement


@pytest.mark.parametrize(
    "polarity,nick,expected",
    [
        ("five_prime", 0, ((9, "A"), (8, "G"), (7, "T"), (6, "C"))),
        ("five_prime", 2, ((7, "A"), (6, "G"), (5, "T"), (4, "C"))),
        ("five_prime", 8, ((1, "A"), (0, "G"))),
        ("three_prime", 0, ((9, "G"), (8, "A"), (7, "C"), (6, "T"))),
    ],
)
def test_required_end_source_contacts_preserve_polarity_and_origin(polarity, nick, expected):
    requirement = BasalFutureReleaseRequirement.model_validate_json(
        '{"product_end":"left","orientation":"forward",'
        f'"cohesive_end_sequence":"AGTC","overhang_end":"{polarity}",'
        '"payload_end_offset_bp":6,"recognition_material":"source_duplex"}'
    )
    assert requirement.source_contact_bases(nick_offset_nt=nick) == expected


@pytest.mark.parametrize("nick", [-1, True, 1.5])
def test_source_contact_projection_rejects_invalid_offsets(nick):
    requirement = BasalFutureReleaseRequirement.model_validate_json(
        '{"product_end":"left","orientation":"forward",'
        '"cohesive_end_sequence":"AGTC","overhang_end":"five_prime",'
        '"payload_end_offset_bp":6}'
    )
    with pytest.raises(ValueError, match="nonnegative integer"):
        requirement.source_contact_bases(nick_offset_nt=nick)
