"""Primer requirements prune exact foldback programs before complete compilation."""

import json

import pytest

from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.product_request import ProductRequest
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def product_with_primers(forward=1, reverse=16, strand="top"):
    data = _two_method_product().model_dump(mode="json", by_alias=True)
    data["foldback"]["geometry"]["nick_strand"] = strand
    policy = data["materialization"]["source_preparation"]
    policy["forward_primer"] = {"mode": "derive", "annealing_length_nt": forward}
    policy["reverse_primer"] = {"mode": "derive", "annealing_length_nt": reverse}
    return ProductRequest.model_validate_json(json.dumps(data))


def test_short_source_program_is_excluded_before_basal_composition(monkeypatch):
    product = product_with_primers(reverse=17)
    plans = PartitionPlans()
    raw = plans._population(product.construction_source().foldback)
    assert raw.parts > 0

    def forbid_basal(*args):
        pytest.fail("A proven short-source foldback must not evaluate basal combinations")

    monkeypatch.setattr(plans, "_basal", forbid_basal)
    plan = plans.get(product)
    assert plan.empty_foldback
    assert plan.foldback.result == raw.result
    proof = plan.foldback.facts()["source_primer_admission"]
    assert proof["excluded_members"] == raw.parts
    assert proof["admitted_members"] == 0
    assert {p["available_nt"] for p in proof["programs"]} == {16}
    assert {p["required_nt"] for p in proof["programs"]} == {17}


@pytest.mark.parametrize("strand,role", [("top", "reverse_primer"), ("bottom", "forward_primer")])
@pytest.mark.parametrize("required", [15, 16, 17])
def test_exact_threshold_and_source_orientation(strand, role, required):
    product = product_with_primers(
        forward=required if role == "forward_primer" else 1,
        reverse=required if role == "reverse_primer" else 1,
        strand=strand,
    )
    plans = PartitionPlans()
    raw = plans._population(product.construction_source().foldback)
    assert raw.parts > 0
    prepared = plans.get(product).foldback
    assert prepared.parts == (raw.parts if required <= 16 else 0)
    proof = prepared.facts()["source_primer_admission"]
    assert {p["primer_role"] for p in proof["programs"]} == {role}
    assert {p["available_nt"] for p in proof["programs"]} == {16}


def test_policy_change_does_not_reuse_an_incompatible_filtered_population():
    plans = PartitionPlans()
    short = product_with_primers(reverse=17)
    permitted = product_with_primers(reverse=16)
    rejected = plans.get(short).foldback
    accepted = plans.get(permitted).foldback
    assert rejected.parts == 0
    assert accepted.parts > 0
    assert rejected.result is accepted.result
    assert plans.get(short).foldback.parts == 0


def test_other_source_side_is_not_excluded_by_the_foldback_span():
    product = product_with_primers(forward=100, reverse=16)
    population = PartitionPlans().get(product).foldback
    assert population.parts > 0
    assert {
        p["primer_role"] for p in population.facts()["source_primer_admission"]["programs"]
    } == {"reverse_primer"}


def test_million_member_population_is_excluded_without_materializing_a_word(monkeypatch):
    from hop_design.models.construction.sequence_sets import SequenceSet

    data = product_with_primers(reverse=37).model_dump(mode="json", by_alias=True)
    data["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[16], junction_offsets_nt=[8], loop_lengths_nt=[12]
    )
    data["foldback"]["search"]["max_retained_overhead_nt"] = 44
    product = ProductRequest.model_validate_json(json.dumps(data))
    plans = PartitionPlans()
    raw = plans._population(product.construction_source().foldback)
    assert raw.parts > 1_000_000

    def forbid_word(*args):
        pytest.fail("Primer-span admission expanded a concrete sequence word")

    monkeypatch.setattr(SequenceSet, "member_at", forbid_word)
    prepared = raw.for_source_preparation(product.materialization.source_preparation)
    assert prepared.parts == 0
    assert {p["available_nt"] for p in prepared.facts()["source_primer_admission"]["programs"]} == {
        36
    }


def test_longer_sequential_precursor_survives_when_same_geometry_single_cut_fails():
    from hop_design.design.construction.surveys.foldback_population import (
        admit_population,
        default_sequence_limits,
        population_request,
    )
    from hop_design.models.construction import FoldbackTarget
    from hop_design.models.enzymes import RecognitionOrientationSemantics
    from hop_design.models.physical import Strand
    from tests.contract.test_foldback_construction_discovery import (
        _nickase,
        _request,
        _terminus_enzyme,
    )

    local = _request(
        _nickase(),
        _terminus_enzyme(
            orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        ),
        target=FoldbackTarget(
            nick_strand=Strand.TOP,
            annealing_arm_length_bp=3,
            junction_offset_nt=0,
            loop_length_nt=3,
        ),
    )
    population = admit_population(population_request(local, default_sequence_limits()), None)
    policy = product_with_primers(forward=10, reverse=10).materialization.source_preparation
    filtered = population.for_source_preparation(policy)
    proof = filtered.facts()["source_primer_admission"]
    assert {p["available_nt"] for p in proof["programs"]} == {9, 13}
    assert {p["kind"] for p in proof["programs"] if p["admitted"]} == {
        "sequential_terminus_plus_nick"
    }
    assert 0 < filtered.parts < population.parts


def short_span_request(tmp_path):
    from tests.unit.test_interface_survey_request import survey_document

    data = survey_document()
    data["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    data["placements"] = [{"left_bp": 6, "right_bp": 6}]
    data["basal"]["annealing_lengths_nt"] = [17]
    data["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[7],
        junction_offsets_nt=[2],
        loop_lengths_nt=[4],
        nick_strand="top",
    )
    data["foldback"]["max_retained_overhead_nt"] = 18
    data["materialization"]["source_preparation"]["reverse_primer"] = {
        "mode": "derive",
        "annealing_length_nt": 17,
    }
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data))
    return path


def test_public_survey_replays_exact_exclusion_without_invoking_whole_compiler(
    tmp_path, monkeypatch
):
    from hop_design import construction
    from hop_design.design.construction.surveys import evaluate

    def forbid_compiler(*args, **kwargs):
        pytest.fail("Whole compiler called for a proven insufficient foldback primer span")

    monkeypatch.setattr(evaluate, "compile_design_from_local_realizations", forbid_compiler)
    path, index = short_span_request(tmp_path), tmp_path / "index.sqlite"
    report = construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=1,
        local_nodes=100,
        local_realizations=100,
        release_site_pairs=10,
    )
    assert report["coverage"]["excluded_pairs"] == 1
    replay = construction.verify_interface_survey(path, index)
    assert replay["coverage"] == report["coverage"]
    assert replay["replayed_evaluations"] == 1


def test_rehashed_primer_span_facts_are_rejected_by_molecular_replay(tmp_path):
    from hop_design import construction
    from hop_design.design.construction.surveys.admission import open_survey
    from hop_design.design.construction.surveys.execute import load_request
    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.design.runtime import producer_identity
    from hop_design.serialization import canonical_json_bytes

    path = short_span_request(tmp_path)
    original, corrupt = tmp_path / "original.sqlite", tmp_path / "corrupt.sqlite"
    construction.evaluate_interface_survey(
        path,
        original,
        max_evaluations=1,
        local_nodes=100,
        local_realizations=100,
        release_site_pairs=10,
    )
    request, producer = load_request(path), producer_identity()
    source, limits = open_survey(original, request=request, producer=producer)
    with (
        source,
        SurveyIndex.create(
            corrupt,
            request=request,
            producer=producer,
            limits=limits.model_dump(mode="json"),
        ) as target,
    ):
        saved = json.loads(source.record(0, step=0))
        target.put_object(source.get_object(saved["product_request"]))
        proof = saved["local_coverage"]["foldback_population"]["source_primer_admission"]
        proof["programs"][0]["available_nt"] += 1
        target.append(
            0, step=0, record=canonical_json_bytes(saved), witness_count=0, exhausted=True
        )
    with pytest.raises(ValueError, match="molecular replay"):
        construction.verify_interface_survey(path, corrupt)
