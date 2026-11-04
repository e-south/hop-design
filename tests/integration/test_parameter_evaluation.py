"""Explicit further evaluation extends a verified pool without losing original choices."""

import json
from pathlib import Path

from hop_design import construction


def test_evaluate_selected_region_keeps_reference_labels_and_retrievable_new_preparation(tmp_path):
    value = json.loads(Path("examples/molecular-editing/request.json").read_bytes())
    value["product"]["foldback"]["geometry"]["loop_sequences"] = ["GAAA", "TTTC"]
    value["max_continuations_per_branch"] = 1
    source = tmp_path / "request.json"
    source.write_text(json.dumps(value))
    original = construction.discover_scaffolds(source).write(tmp_path / "initial")
    pool = construction.load_scaffold_exploration(original)
    before = json.loads(pool.json_bytes)
    assert len(before["options"]) == 1
    reference = before["options"][0]["label"]
    selected = construction.query_scaffold_variants(
        pool,
        {
            "schema": "hop.scaffold-variant-query/v2",
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
            "reference": reference,
            "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
            "parameters": [{"key": "loop_word", "values": ["TTTC"]}],
        },
    )
    assert json.loads(selected.json_bytes)["compatible_options"] == []
    packet = construction.evaluate_scaffold_parameters(
        pool, selected, max_branches=1, max_continuations_per_branch=1
    )
    extended = packet.write(tmp_path / "extended")
    expanded = construction.load_scaffold_exploration(extended)
    observations = json.loads(expanded.json_bytes)
    assert len(observations["options"]) == 2
    assert observations["options"][0]["label"] == reference
    assert (
        observations["options"][0]["molecular_identity"]
        == before["options"][0]["molecular_identity"]
    )
    query = json.loads(selected.json_bytes)["query"]
    query["result_digest"] = expanded.result_digest
    refreshed = construction.query_scaffold_variants(expanded, query)
    facts = json.loads(refreshed.json_bytes)
    assert facts["query"]["parameters"] == query["parameters"]
    assert facts["query"]["reference"] == reference
    assert len(facts["compatible_options"]) == 1
    label = facts["compatible_options"][0]
    assert label != reference
    preparation = construction.select_scaffold_variants(
        extended, refreshed, members={"selected": label}, baseline="selected"
    )
    assert b"TTTC" in preparation.json_bytes or b"TTTC" in dict(preparation._files)["oligos.csv"]
    # A repeated evaluation is a separate coverage record, not a new molecule.
    repeated = construction.evaluate_scaffold_parameters(
        expanded, refreshed, max_branches=1, max_continuations_per_branch=1
    ).write(tmp_path / "repeated")
    repeated_pool = construction.load_scaffold_exploration(repeated)
    repeated_facts = json.loads(repeated_pool.json_bytes)
    assert len(repeated_facts["options"]) == 2
    records = repeated_facts["parameter_branch_coverage"]
    assert len({r["coverage_record_id"] for r in records}) == len(records)
    assert (
        sum(r["status"] == "evaluated" for r in records)
        == repeated_facts["coverage"]["evaluated_branches"]
    )
    # Both original and new packets remain independently verifiable.
    assert construction.load_scaffold_exploration(original).result_digest == pool.result_digest


def test_browser_evaluation_requires_current_query_and_keeps_filters(loop_options, tmp_path):
    import pytest

    from hop_design.commands.construction.editor.variants import VariantSession

    session = VariantSession(loop_options[0], tmp_path / "session")
    state = session.state()
    query = state["choices"]["query"]
    query.update(
        schema="hop.scaffold-variant-query/v2",
        parameters=[{"key": "self_paired_arm_bp", "minimum": 7, "maximum": 7}],
    )
    state = session.query(query)
    old_options = state["pool"]["options"]
    old_result = state["pool"]["result_digest"]
    with pytest.raises(ValueError, match="Stale"):
        session.evaluate_parameters(
            {"query_digest": "stale", "max_branches": 1, "max_continuations_per_branch": 1}
        )
    result = session.evaluate_parameters(
        {
            "query_digest": state["choices"]["query_digest"],
            "max_branches": 1,
            "max_continuations_per_branch": 1,
        }
    )
    assert result["pool"]["result_digest"] != old_result
    assert result["pool"]["options"][: len(old_options)] == old_options
    assert result["choices"]["query"]["parameters"] == state["choices"]["query"]["parameters"]
    assert result["evaluation"]["additional_coverage"]["evaluated_branches"] == 1
