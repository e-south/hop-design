"""One explicit stem family shares the ordinary intent-to-preparation lifecycle."""

import json
import shlex
import shutil

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_design_discovery import intent_document


def family_intent():
    request = intent_document()
    return {
        **request,
        "schema": "hop.construction-family-intent/v1",
        "stem_arm": "N" + request["stem_arm"][1:],
        "max_members": 4,
        "max_total_evaluations": 16,
        "shared_properties": ["non_stem_sequences"],
        "shared_material_roles": ["source_materialization_forward_primer"],
    }


def test_family_preview_is_bounded_and_preserves_optional_ends(tmp_path):
    request = family_intent()
    preview = construction.resolve_design_request(request)
    summary = json.loads(preview.json_bytes)
    assert summary["required_members"] == 4
    assert {m["stem_arm"][0] for m in summary["members"]} == set("ACGT")
    assert all(m["request"]["ends"] is None for m in summary["members"])
    assert summary["execution"] == "not_started"
    with pytest.raises(ValueError, match="max_members"):
        construction.discover_designs(
            {**request, "max_members": 3}, tmp_path / "too-many", max_evaluations=4
        )
    assert not (tmp_path / "too-many").exists()
    with pytest.raises(ValueError, match="max_total_evaluations"):
        construction.discover_designs(request, tmp_path / "too-much", max_evaluations=17)
    assert not (tmp_path / "too-much").exists()
    with pytest.raises(ValueError, match="First-choice"):
        construction.discover_designs(
            request, tmp_path / "bad-policy", max_evaluations=4, first_choices=1
        )
    assert not (tmp_path / "bad-policy").exists()


def test_family_members_roundtrip_without_another_search_engine(tmp_path, monkeypatch):
    directory = tmp_path / "family results"
    choices = construction.discover_designs(family_intent(), directory, max_evaluations=16)
    answer = choices.query()
    assert answer["required_members"] == 4
    assert answer["missing_members"] == []
    assert all(m["complete_preparations"] > 0 for m in answer["members"])
    members = {
        m["name"]: choices.member(m["name"]).sample(
            seed=0, query={"parameters": [{"key": "left_end_word", "values": ["AAAC"]}]}
        )
        for m in answer["members"]
    }
    different = {
        **members,
        "member-0004": choices.member("member-0004").sample(
            seed=0, query={"parameters": [{"key": "left_end_word", "values": ["AAAG"]}]}
        ),
    }
    with pytest.raises(ValueError, match="shared properties"):
        choices.select_members(different, baseline="member-0001")
    selected = choices.select_members(members, baseline="member-0001")
    runner = CliRunner()
    queried = runner.invoke(
        app,
        [
            "design",
            "query",
            str(directory),
            "--member",
            "member-0001",
            "--format",
            "json",
        ],
    )
    assert queried.exit_code == 0, queried.output
    assert json.loads(queried.output) == choices.member("member-0001").query()
    # Readable feedback must preserve the same required stem and query when followed.
    member = choices.member("member-0001")
    filtering = {"parameters": [{"key": "left_end_word", "values": ["AAAC"]}]}
    query_path = tmp_path / "selected ends.json"
    query_path.write_text(json.dumps(filtering))
    readable = runner.invoke(
        app,
        [
            "design",
            "query",
            str(directory),
            "--member",
            "member-0001",
            "--query",
            str(query_path),
            "--format",
            "text",
        ],
    )
    assert readable.exit_code == 0, readable.output
    commands = {
        prefix: shlex.split(line.split(": ", 1)[1])[1:]
        for line in readable.output.splitlines()
        for prefix in ("Inspect", "Sample", "Full records and coverage", "Family search bounds")
        if line.startswith(prefix + ": ")
    }
    for prefix in ("Inspect", "Sample", "Full records and coverage"):
        assert "--member" in commands[prefix], readable.output
        assert commands[prefix][commands[prefix].index("--member") + 1] == "member-0001"
    assert commands["Inspect"][2] == str(directory)
    sampled = commands["Sample"]
    sampled[sampled.index("--out") + 1] = str(tmp_path / "suggested selection.json")
    result = runner.invoke(app, sampled)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == member.sample(seed=1, query=filtering)
    records = runner.invoke(app, commands["Full records and coverage"])
    assert records.exit_code == 0, records.output
    assert json.loads(records.output) == member.query(filtering)
    # Member feedback cannot promise an evaluation beyond its family's bound.
    assert "Search further:" not in readable.output
    bounds = commands["Family search bounds"]
    assert "--member" not in bounds and bounds[2] == str(directory)
    result = runner.invoke(app, bounds)
    assert result.exit_code == 0, result.output
    assert choices.explain()["headline"] in result.output

    # Admit the printed inspect command normally; only the blocking server loop is replaced.
    from hop_design.commands import design as design_cli

    create_server = design_cli.create_design_server
    inspected = []

    def bounded_server(*args, **kwargs):
        server = create_server(*args, **kwargs)
        inspected.append(server.session.state()["explanation"])
        server.serve_forever = lambda: None
        return server

    monkeypatch.setattr(design_cli, "create_design_server", bounded_server)
    inspect = commands["Inspect"]
    inspect[inspect.index("--out") + 1] = str(tmp_path / "suggested inspection")
    result = runner.invoke(app, inspect)
    assert result.exit_code == 0, result.output
    assert inspected == [member.explain()]
    path = tmp_path / "membership.json"
    path.write_text(json.dumps(members))
    selected_cli = runner.invoke(
        app,
        [
            "design",
            "select-members",
            str(directory),
            "--members",
            str(path),
            "--baseline",
            "member-0001",
        ],
    )
    assert selected_cli.exit_code == 0, selected_cli.output
    assert json.loads(selected_cli.output) == selected
    with pytest.raises(ValueError, match="every required member"):
        choices.select_members({"member-0001": members["member-0001"]}, baseline="member-0001")
    shutil.copytree(directory, tmp_path / "relocated")
    restored = construction.load_design_choices(tmp_path / "relocated")
    receipt = restored.retrieve(selected, tmp_path / "handoff")
    assert len(receipt.materialized_realization_ids) == 4
    assert json.loads((tmp_path / "handoff/design-selection.json").read_bytes()) == selected
    edited = json.loads(json.dumps(selected))
    edited["members"]["member-0001"] = edited["members"]["member-0002"]
    edited["selection_digest"] = sha256_digest(
        canonical_json_bytes({k: v for k, v in edited.items() if k != "selection_digest"})
    )
    with pytest.raises(ValueError):
        restored.retrieve(edited, tmp_path / "wrong-stem")
    assert not (tmp_path / "wrong-stem").exists()
    assert (tmp_path / "handoff/oligos.csv").is_file()
    assert (tmp_path / "handoff/oligo-uses.csv").is_file()
    summary = json.loads((tmp_path / "handoff/summary.json").read_bytes())
    assert all(
        c["status"] == "required_and_verified"
        for c in summary["comparison_controls"]
        if c["required"]
    )
    with pytest.raises(ValueError, match="max_total_evaluations"):
        restored.find_more(max_evaluations=1)


def test_exact_stem_boundary_explains_family_request():
    request = intent_document()
    request["stem_arm"] = "N" + request["stem_arm"][1:]
    with pytest.raises(ValueError, match="construction-family-intent"):
        construction.resolve_design_request(request)


def test_partial_family_retains_required_missing_members_and_continues(tmp_path):
    choices = construction.discover_designs(
        family_intent(), tmp_path / "partial", max_evaluations=2
    )
    assert choices.query()["missing_members"] == ["member-0003", "member-0004"]
    assert "continue_search" in choices.explain()["actions"]
    assert "select_members" not in choices.explain()["actions"]
    completed = choices.find_more(max_evaluations=2)
    assert completed.query()["missing_members"] == []
    assert completed.query()["reserved_evaluations"] == 4
