"""The exploration example declares a bounded open domain, not a preferred shortlist."""

import json
from pathlib import Path


def test_example_leaves_foldback_geometry_and_words_open_with_explicit_budgets():
    v = json.loads(Path("examples/molecular-editing/construction-envelope.json").read_text())
    g, search = v["product"]["foldback"]["geometry"], v["product"]["foldback"]["search"]
    assert not g["annealing_arm_lengths_bp"]
    assert not g["loop_lengths_nt"]
    assert g.get("loop_sequences") is None
    assert g["junction_offsets_nt"] == list(range(search["max_retained_overhead_nt"] // 2 + 1))
    assert not v.get("parameters")
    assert v["max_continuations_per_branch"] >= search["result_quota"]
    assert v["product"]["whole_route_constraints"]["require_exact_materials"]


def test_numeric_domain_marks_reveal_interiors_without_enumerating_large_domains():
    from hop_design.design.construction.variants.parameters.filter import domain_marks

    assert domain_marks({"minimum": 3, "maximum": 6}) == {3, 4, 5, 6}
    assert len(domain_marks({"minimum": 0, "maximum": 1_000_000})) <= 7
    assert domain_marks(
        {"intervals": [{"minimum": 1, "maximum": 3}, {"minimum": 8, "maximum": 9}]}
    ) == {1, 2, 3, 8, 9}
