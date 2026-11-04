"""Reference-bound matching preserves requirements, coverage and explicit selection."""

import json
import shutil

import pytest

from hop_design import construction
from tests.integration.test_construction_family import family_path


@pytest.fixture(scope="module")
def mismatched_family(tmp_path_factory):
    root = tmp_path_factory.mktemp("family-matching")
    path = family_path(root)
    request = json.loads(path.read_text())
    request["members"] = [{"name": "loop3", "loop_nt": 3}, {"name": "loop4", "loop_nt": 4}]
    request["base_request"]["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [7, 8]
    request["base_request"]["foldback"]["search"].update(max_realizations=8, result_quota=8)
    request["shared_properties"] += [
        "loop_side_paired_bp",
        "non_loop_sequences",
        "regional_contacts",
        "regional_joins",
    ]
    path.write_text(json.dumps(request))
    construction.execute_construction_family(path, continuation="sole-witness").write(
        root / "stopped"
    )
    for name, extension in (("loop3", 7), ("loop4", 8)):
        member = root / "stopped/members" / name
        prepared = construction.prepare_construction_request(member / "request.json")
        inputs = prepared.write(root / (name + "-inputs"))
        ids = {}
        for local in ("foldback", "basal"):
            receipt = construction.discover_local_neighborhood(inputs / (local + ".json"))
            saved = receipt.write(root / (name + "-" + local))
            choices = construction.list_local_realizations(receipt)
            chosen = next(
                c
                for c in choices
                if local == "basal" or c.geometry.annealing_arm_length_bp == extension
            )
            ids[local + "_path"] = saved / "result.json"
            ids[local + "_realization_id"] = chosen.realization_id
        construction.continue_construction_request(
            member / "request.json", design_id="selected-" + name, **ids
        ).write(root / (name + "-outcome"))
    for label, members in (("forward", request["members"]), ("reverse", request["members"][::-1])):
        request["members"] = members
        path.write_text(json.dumps(request))
        saved = construction.execute_construction_family(path, continuation="sole-witness").write(
            root / label
        )
        for i, name in enumerate(("loop3", "loop4")):
            saved = construction.reconcile_construction_family(
                saved, source_member=name, outcome_path=root / (name + "-outcome")
            ).write(root / f"{label}-{i}")
    return root


def test_matching_finds_complete_alternative_against_explicit_reference(
    mismatched_family, tmp_path
):
    root = mismatched_family
    before = json.loads((root / "forward-1/summary.json").read_text())
    assert before["display_order"] == ["loop3"]
    packet = construction.match_construction_family(
        root / "forward-1", reference_member="loop3", reference_choice=0, max_continuations=2
    )
    result = json.loads(packet.json_bytes)
    assert result["reference"]["member"] == "loop3"
    assert result["coverage"]["evaluated_pairs"] == 2
    assert result["coverage"]["recorded_pairs"] == 2
    assert result["coverage"]["global_family_feasibility"] == "not_assessed"
    member = result["members"][0]
    assert member["name"] == "loop4"
    assert member["original_choices"][0]["compatible"] is False
    assert [c["choices"][0]["compatible"] for c in member["candidates"]] == [True, False]
    assert "loop_side_paired_bp" in member["original_choices"][0]["differing_properties"]
    packet.write(tmp_path / "matched")
    chosen = member["candidates"][0]["choices"][0]
    selection = {
        "schema": "hop.construction-set/v1",
        "baseline": "loop3",
        "members": [
            {"name": "loop3", **result["reference"]["selection"]},
            {"name": "loop4", **chosen["selection"]},
        ],
        "shared_properties": result["shared_properties"],
        "compared_properties": ["loop_nt"],
    }
    for member_request in selection["members"]:
        for key in ("bundle_path", "selection_path"):
            member_request[key] = "matched/" + member_request[key]
    request = tmp_path / "chosen.json"
    request.write_text(json.dumps(selection))
    selected = construction.select_construction_set(request).write(tmp_path / "set")
    shutil.move(selected, tmp_path / "relocated")
    assert construction.select_construction_set(tmp_path / "relocated/set.json").json_bytes
    assert (root / "forward-1/summary.json").read_text() == json.dumps(
        before, sort_keys=True, separators=(",", ":")
    ) + "\n"


def test_matching_is_independent_of_roster_order_and_retains_truncation(mismatched_family):
    results = []
    for label in ("forward-1", "reverse-1"):
        packet = construction.match_construction_family(
            mismatched_family / label,
            reference_member="loop3",
            reference_choice=0,
            max_continuations=1,
        )
        summary = json.loads(packet.json_bytes)
        assert summary["coverage"]["evaluated_pairs"] == 1
        assert summary["coverage"]["recorded_pairs"] == 2
        assert summary["coverage"]["completion"] == "stopped_by_bound"
        assert summary["members"][0]["unexamined_pairs"] == 1
        results.append(summary["members"])
    assert results[0] == results[1]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reference_member": "missing", "reference_choice": 0, "max_continuations": 1},
        {"reference_member": "loop3", "reference_choice": 99, "max_continuations": 1},
        {"reference_member": "loop3", "reference_choice": 0, "max_continuations": 0},
    ],
)
def test_matching_rejects_undeclared_reference_or_budget(mismatched_family, kwargs):
    with pytest.raises(ValueError):
        construction.match_construction_family(mismatched_family / "forward-1", **kwargs)


def test_matching_cli_parity_and_existing_output(mismatched_family, tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    source = mismatched_family / "forward-1"
    expected = construction.match_construction_family(
        source, reference_member="loop3", reference_choice=0, max_continuations=1
    )
    args = [
        "construction",
        "match-family",
        str(source),
        "--reference-member",
        "loop3",
        "--reference-choice",
        "0",
        "--max-continuations",
        "1",
        "--out",
        str(tmp_path / "match"),
    ]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "match/summary.json").read_bytes() == expected.json_bytes
    assert CliRunner().invoke(app, args).exit_code != 0


def test_matching_rejects_damaged_authority(mismatched_family, tmp_path):
    source = tmp_path / "damaged"
    shutil.copytree(mismatched_family / "forward-1", source)
    (source / "members/loop3/request.json").write_text("{}")
    with pytest.raises(ValueError):
        construction.match_construction_family(
            source, reference_member="loop3", reference_choice=0, max_continuations=1
        )


def test_reconciled_family_leads_with_molecules_then_recovery(mismatched_family, tmp_path):
    from xml.etree import ElementTree as ET

    output = construction.project_construction_family_report(
        mismatched_family / "forward-1", baseline="loop3"
    ).write(tmp_path / "report")
    pages = sorted((output / "pages").glob("*.svg"))
    assert "Compare the scaffold" in " ".join(ET.parse(pages[0]).getroot().itertext())
    assert "Continue an explicit" in " ".join(ET.parse(pages[1]).getroot().itertext())
