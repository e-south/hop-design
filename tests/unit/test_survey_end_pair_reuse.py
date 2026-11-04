"""The basal/end relation does not depend on closing-region geometry."""

from hop_design.design.construction.surveys.completion.interfaces import EndPairRelations
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import policy
from tests.unit.test_survey_completion_binding import product


def test_changed_foldback_reuses_only_the_necessary_end_relation():
    p = product()
    q = p.model_copy(
        update={
            "foldback": p.foldback.model_copy(
                update={
                    "geometry": p.foldback.geometry.model_copy(update={"loop_lengths_nt": (5,)})
                }
            )
        }
    )
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    assert cache.relation(p) is cache.relation(q)


def test_source_base_permissions_and_association_lengths_remain_cache_dependencies():
    p = product()
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    assert cache.relation(p).cardinality == 256
    constraints = tuple(
        c.model_copy(update={"allowed_source_bases": ("A",)})
        if c.position_from_ligation == 9
        else c
        for c in p.basal.geometry.pairing_constraints
    )
    restricted = p.model_copy(
        update={
            "basal": p.basal.model_copy(
                update={
                    "geometry": p.basal.geometry.model_copy(
                        update={"pairing_constraints": constraints}
                    )
                }
            )
        }
    )
    relation = cache.relation(restricted)
    assert relation.cardinality == 64
    assert all(relation.member_at(i).startswith("A") for i in range(64))
    assert cache.relation(product(anneal=10)).cardinality == 0
