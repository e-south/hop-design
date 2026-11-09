"""Named release methods remain distinct while sharing identical necessary geometry."""

import json

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.design.construction.surveys.completion.interfaces import EndPairRelations
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.serialization import canonical_json_bytes
from tests.support.context_completion import policy
from tests.unit.test_survey_completion_binding import product

ALIAS = "example:enzyme/zz-equivalent-release@1"


def products(*, changes=None, blocked=None, multiple_basal=False):
    data = product().model_dump(mode="json", by_alias=True)
    original_id = data["release"]["enzymes"]["allowed_enzyme_ids"][0]
    original = next(e for e in data["enzyme_catalog"]["enzymes"] if e["enzyme_id"] == original_id)
    data["enzyme_catalog"]["enzymes"].append(
        {**original, "enzyme_id": ALIAS, "canonical_name": "Equivalent example", **(changes or {})}
    )
    for family in ("basal", "release"):
        data[family]["enzymes"]["allowed_enzyme_ids"].append(ALIAS)
    if blocked:
        if blocked == "allowed_enzyme_ids":
            data["basal"]["enzymes"][blocked].remove(ALIAS)
        else:
            data["basal"]["enzymes"]["allowed_enzyme_ids"] = []
            data["basal"]["enzymes"][blocked] = [ALIAS]
    if multiple_basal:
        next(
            r
            for r in data["basal"]["enzymes"]["role_restrictions"]
            if r["role"] == "end_generation"
        )["allowed_enzyme_ids"] = [original_id, ALIAS]
    first = ProductRequest.model_validate_json(json.dumps(data))
    for family in ("release",) if multiple_basal else ("basal", "release"):
        next(
            r for r in data[family]["enzymes"]["role_restrictions"] if r["role"] == "end_generation"
        )["allowed_enzyme_ids"] = [ALIAS]
    return first, ProductRequest.model_validate_json(json.dumps(data))


def test_identical_release_definition_reuses_only_the_necessary_relation():
    first, second = products()
    before = canonical_json_bytes((first.model_dump(mode="json"), second.model_dump(mode="json")))
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    relation = cache.relation(first)
    assert relation.cardinality > 0
    assert cache.relation(second) is relation
    assert canonical_json_bytes(
        (first.model_dump(mode="json"), second.model_dump(mode="json"))
    ) == (before)
    # Caching geometry must not replace either method in the actual program stream.
    names = []
    for p in (first, second):
        names.append(
            {
                str(unit.program.future_release_enzyme.enzyme_id)
                for unit in iter_basal_work_units(
                    p.construction_source().basal, retained_overhead_nt=None
                )
            }
        )
    assert names[0] != names[1] == {ALIAS}


@pytest.mark.parametrize(
    "changes",
    [
        {"cut_offset_reference_strand": 8, "cut_offset_complement_strand": 12},
        {"recognition_pattern": "GGTACC"},
    ],
)
def test_changed_cleavage_or_recognition_cannot_reuse_the_definition(changes):
    first, second = products(changes=changes)
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    assert cache.relation(first) is not cache.relation(second)


@pytest.mark.parametrize("blocked", ["forbidden_enzyme_ids", "reserved_enzyme_ids"])
@pytest.mark.parametrize("reverse", [False, True])
def test_basal_permissions_are_checked_before_definition_reuse(blocked, reverse):
    first, second = products(blocked=blocked)
    values = (second, first) if reverse else (first, second)
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    for p in values:
        if p is second:
            # Explicitly authorizing a forbidden/reserved method is malformed,
            # not a complete empty molecular relation or a reusable alias.
            with pytest.raises(ValidationError, match="must not authorize"):
                cache.relation(p)
        else:
            expected = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS).relation(p)
            assert cache.relation(p) == expected
    assert cache.relation(first).cardinality > 0


def test_inconsistent_allowlist_raises_before_a_warm_definition_lookup():
    first, second = products(blocked="allowed_enzyme_ids")
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    assert cache.relation(first).cardinality > 0
    with pytest.raises(ValidationError, match="globally allowed"):
        cache.relation(second)


def test_multiple_basal_release_choices_keep_the_original_key():
    first, second = products(multiple_basal=True)
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    assert cache.relation(first) is not cache.relation(second)


def test_different_singletons_at_the_two_roles_keep_the_original_key():
    first, second = products()
    changed = second.model_copy(update={"basal": first.basal})
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    assert cache.relation(first) is not cache.relation(changed)


def test_catalog_changes_remain_dependencies_even_for_equal_geometry():
    first, second = products()
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    reference = cache.relation(first)
    changed = second.model_dump(mode="json", by_alias=True)
    changed["enzyme_catalog"]["catalog_id"] = "example:catalog/another@1"
    assert cache.relation(ProductRequest.model_validate_json(json.dumps(changed))) is not reference
