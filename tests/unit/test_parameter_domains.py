"""Browse a bounded domain without confusing permission, evidence and feasibility."""

import json

from hop_design.design.construction.variants.parameters.domains import parameter_domains
from tests.unit.test_envelope_revision import seed


def test_unfixed_words_are_paged_without_allocating_the_sequence_space():
    from hop_design.design.construction.variants.parameters.browse import domain_values

    domains = {
        "loop_word": {"alphabet": "ACGT", "length_parameter": "loop_nt"},
        "loop_nt": {"minimum": 3, "maximum": 26},
    }
    page = domain_values(domains, "loop_word", length=20, prefix="T", offset=0, limit=4)
    assert page["total"] == 4**19
    assert page["values"] == [
        "T" + "A" * 19,
        "T" + "A" * 18 + "C",
        "T" + "A" * 18 + "G",
        "T" + "A" * 18 + "T",
    ]
    assert page["next_offset"] == 4
    assert page["scope"] == "permitted_domain_not_complete_preparations"


def test_integer_paging_includes_unobserved_interior_values_and_respects_holes():
    from hop_design.design.construction.variants.parameters.browse import domain_values

    domains = {
        "foldback_arm_bp": {
            "intervals": [{"minimum": 3, "maximum": 6}, {"minimum": 10, "maximum": 12}]
        }
    }
    page = domain_values(domains, "foldback_arm_bp", offset=2, limit=4)
    assert page["values"] == [5, 6, 10, 11]
    assert page["total"] == 7


def test_domain_browse_cannot_invent_sequence_lengths_or_words():
    import pytest

    from hop_design.design.construction.variants.parameters.browse import domain_values

    domains = parameter_domains(seed())
    assert domain_values(domains, "loop_word", length=4)["values"] == ["GAAA", "TTTC"]
    assert domain_values(domains, "loop_word", length=4, prefix="A")["values"] == []
    for kwargs in (
        {"length": 20},
        {"length": 4, "prefix": "N"},
        {"limit": 0},
        {"offset": -1},
        {"limit": 10000},
    ):
        with pytest.raises(ValueError):
            domain_values(domains, "loop_word", **kwargs)


def test_domain_browse_request_rejects_unknown_keys_and_non_integer_bounds():
    import pytest

    from hop_design.models.construction.variants.domain import ParameterDomainQuery

    for value in (
        {"key": "invented"},
        {"key": "foldback_arm_bp", "offset": True},
        {"key": "foldback_arm_bp", "limit": 1.5},
    ):
        with pytest.raises(ValueError):
            ParameterDomainQuery.model_validate_json(json.dumps(value))
