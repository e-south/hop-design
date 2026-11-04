"""Joint end exclusions remain distinct from marginal availability and global coverage."""

from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.surveys.targets import InterfaceTargetDomain


def test_joint_exclusion_does_not_require_excluding_either_word_everywhere():
    from hop_design.design.construction.surveys.selection import interfaces_excluded

    domain = InterfaceTargetDomain(left_words=("AGTC", "AAAA"), right_words=("AACC", "AAAA"))
    excluded = (("AGTC", "AACC"),)
    query = InterfaceSurveyQuery.model_validate_json(
        '{"parameters":[{"key":"left_end_word","values":["AGTC"]},{"key":"right_end_word","values":["AACC"]}]}'
    )
    assert interfaces_excluded(domain, excluded, query)
    assert not interfaces_excluded(domain, excluded, InterfaceSurveyQuery())
    left_only = InterfaceSurveyQuery.model_validate_json(
        '{"parameters":[{"key":"left_end_word","values":["AGTC"]}]}'
    )
    assert not interfaces_excluded(domain, excluded, left_only)


def test_continuation_uses_query_targets_and_recorded_end_addresses():
    from hop_design.design.construction.surveys.selection import interfaces_pending

    domain = InterfaceTargetDomain(left_words=("AGTC", "AAAA"), right_words=("AACC", "AAAA"))
    ended = (("AGTC", "AACC"),)
    query = InterfaceSurveyQuery.model_validate_json(
        '{"parameters":[{"key":"left_end_word","values":["AGTC"]},{"key":"right_end_word","values":["AACC"]}]}'
    )
    assert not interfaces_pending(domain, ended, query)
    assert interfaces_pending(domain, ended, InterfaceSurveyQuery())
    # A witness with a pending continuation can still yield more preparations.
    assert interfaces_pending(domain, (), query)
    outside = InterfaceSurveyQuery.model_validate_json(
        '{"parameters":[{"key":"left_end_word","values":["TGCA"]}]}'
    )
    assert not interfaces_pending(domain, ended, outside)
