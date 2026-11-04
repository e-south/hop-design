"""Complete routes may reverse contact notation without changing their substrate."""

from collections import defaultdict

from hop_design import construction
from hop_design.design.construction.intents.inserts.admission import admitted_options
from tests.integration.test_design_discovery import intent_document


def test_alternate_foldback_preparations_share_product_identity(tmp_path):
    request = intent_document()
    request["ends"] = {"left": "AAAA", "right": "AAAA"}
    context = request["context"]
    context["source_context_objective"] = "paired_scaffold_completions"
    context["foldback"]["geometry"]["nick_strand"] = "any"
    old, new = "example:enzyme/bsai-hfv2@1", "example:enzyme/bsmbi-v2@1"
    enzyme = next(e for e in context["enzyme_catalog"]["enzymes"] if e["enzyme_id"] == old)
    enzyme.update(enzyme_id=new, canonical_name="BsmBI-v2", recognition_pattern="CGTCTC")
    for region in ("basal", "release"):
        permission = context[region]["enzymes"]
        for declaration in (permission, *permission["role_restrictions"]):
            declaration["allowed_enzyme_ids"] = [
                new if value == old else value for value in declaration["allowed_enzyme_ids"]
            ]
    source = context["materialization"]["source_preparation"]
    source["source_ssdna"]["upstream_sequence_spec"] = {
        "base_spec": "N",
        "min_length_nt": 14,
        "max_length_nt": 22,
    }
    for role in ("forward_primer", "reverse_primer"):
        source[role] = {
            "mode": "constrain",
            "min_annealing_length_nt": 14,
            "max_annealing_length_nt": 24,
        }
    choices = construction.discover_designs(request, tmp_path / "choices", max_evaluations=8)
    by_content = defaultdict(list)
    for option in admitted_options(choices):
        state = option["portrait_data"]["state"]
        strands = tuple(
            (s["sequence"], s["five_prime_end"], s["three_prime_end"]) for s in state["molecules"]
        )
        contacts = frozenset(
            (
                frozenset(((p["left_index"], p["left_base"]), (p["right_index"], p["right_base"]))),
                p["kind"],
            )
            for p in state["pairings"]
        )
        by_content[strands, contacts].append(option)
    pair = next(
        group
        for group in by_content.values()
        if len({p["values"]["foldback_strand"] for p in group}) == 2
    )
    assert len({p["materialized_realization_id"] for p in pair}) == 2
    assert len({p["molecular_identity"]["hairpin"] for p in pair}) == 1
    for stage in ("hairpin", "endpoint"):
        brief = {
            "stage": stage,
            "required_members": [{"name": n, "loop_sequence": "AAAG"} for n in ("a", "b")],
            "max_group_evaluations": 16,
        }
        ids = {p["materialized_realization_id"] for p in pair}
        alternatives = choices.compare({**brief, "purpose": "preparation_alternatives"})["sets"]
        assert any(set(s["members"].values()) == ids for s in alternatives)
        distinct = choices.compare({**brief, "purpose": "distinct_substrates"})["sets"]
        assert not any(set(s["members"].values()) == ids for s in distinct)
