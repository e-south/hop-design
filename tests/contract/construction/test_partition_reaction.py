"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/construction/test_partition_reaction.py

Checks exact cleanup-nick programs derived from a selected source partition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest
import yaml

from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction.complete.source_partition.reaction import (
    derive_partition_reaction_program,
)
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryRequest
from hop_design.models.reaction_replay import assess_reaction_program


def _span(start, end):
    return {"start": {"offset": start}, "end": {"offset": end}}


def _partition(maximum_nt=12):
    example = Path(__file__).resolve().parents[3] / "examples/basal-junction/request.yaml"
    payload = yaml.safe_load(example.read_text())["payload"]
    source = "GCTACCTAGTGA" * 2 + payload["payload"]["sequence"] + "CGATGACC"
    enzymes = []
    for name, motif, top, bottom in (
        ("repeat", "GGTAGC", 1, None),
        ("terminal", "CGATGACC", 4, None),
    ):
        enzymes.append(
            {
                "enzyme_id": f"example:enzyme/{name}@1",
                "canonical_name": name,
                "enzyme_class": "nickase",
                "target_molecule": "dna",
                "recognition_pattern": motif,
                "recognition_orientation_semantics": "both_orientations",
                "recognition_length": len(motif),
                "substrate_requirement": "duplex_dna",
                "cut_offset_reference_strand": top,
                "cut_offset_complement_strand": bottom,
                "resulting_end_model": "nick",
                "characterization_source": {"system": "synthetic-test", "kind": "rule", "id": name},
                "vendor_metadata": [],
            }
        )
    ids = tuple(item["enzyme_id"] for item in enzymes)
    request = SourcePartitionDiscoveryRequest.model_validate_json(
        json.dumps(
            {
                "payload": payload,
                "source": {
                    "material_id": "source",
                    "top_sequence_5prime": source,
                    "top_five_prime_end": "hydroxyl",
                    "top_three_prime_end": "hydroxyl",
                    "bottom_five_prime_end": "phosphate",
                    "bottom_three_prime_end": "hydroxyl",
                },
                "payload_source_map": {
                    "segments": [
                        {
                            "payload_span": _span(0, 34),
                            "source_material_id": "source",
                            "source_span": _span(24, 58),
                            "orientation": "forward",
                        }
                    ]
                },
                "enzyme_provisioning": {
                    "catalog": {
                        "catalog_id": "example:enzyme-catalog/cleanup@1",
                        "enzymes": enzymes,
                    },
                    "allowed_enzyme_ids": ids,
                    "forbidden_enzyme_ids": [],
                    "reserved_enzyme_ids": [],
                    "max_operations": 3,
                    "role_restrictions": [],
                },
                "constraints": {
                    "fragment_policy": {
                        "preferred_maximum_nt": maximum_nt,
                        "absolute_maximum_nt": maximum_nt,
                    },
                    "required_survivors": [
                        {
                            "survivor_id": "retained-top",
                            "precursor_strand": "top",
                            "source_span": _span(0, 62),
                        },
                        {
                            "survivor_id": "retained-bottom",
                            "precursor_strand": "bottom",
                            "source_span": _span(17, 66),
                        },
                    ],
                    "max_enzymes_per_program": 2,
                },
                "enumeration": {"max_search_nodes": 3, "max_realizations": 3},
            }
        )
    )
    result = discover_source_partitions(request)
    assert result.status == "complete"
    assert len(result.realizations) == 1
    return result


@pytest.mark.parametrize("maximum_nt", (12, 13))
def test_partition_compiles_every_nick_before_actionable_site_assessment(maximum_nt):
    result = _partition(maximum_nt)
    selected = result.realizations[0]
    program = derive_partition_reaction_program(selected)
    assert len(program.stages) == 1
    stage = program.stages[0]
    cuts = {
        ("top", op.intended_binding.reference_cut.offset)
        if op.intended_binding.reference_cut is not None
        else ("bottom", op.intended_binding.complement_cut.offset)
        for op in stage.operations
    }
    assert cuts == {
        ("bottom", 5),
        ("bottom", 17),
        ("top", 62),
    }
    assert sorted(len(m.reference_sequence_5prime) for m in program.states[-1].molecules) == [
        4,
        5,
        12,
        49,
        62,
    ]
    assert tuple(m.reference_sequence_5prime for m in program.states[-1].molecules) == tuple(
        fragment.sequence for fragment in selected.denatured.fragments
    )
    assessment = assess_reaction_program(program=program, policy=result.request.enzyme_provisioning)
    assert not assessment.report.has_errors
    assert not assessment.stage_assessments[0].undeclared_bindings

    missing_cut = program.model_copy(
        update={
            "stages": (stage.model_copy(update={"operations": stage.operations[1:]}),),
        }
    )
    missing = assess_reaction_program(
        program=missing_cut, policy=result.request.enzyme_provisioning
    )
    assert missing.report.has_errors
    assert len(missing.stage_assessments[0].undeclared_bindings) == 1


def test_fragment_cutoff_does_not_change_the_same_molecular_reaction():
    lower = _partition(12)
    upper = _partition(13)
    assert lower.result_id != upper.result_id
    assert derive_partition_reaction_program(
        lower.realizations[0]
    ) == derive_partition_reaction_program(upper.realizations[0])
