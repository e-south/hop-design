"""Product exploration returns complete choices before any local witness selection."""

import json
import shutil

import pytest

from hop_design import construction
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_request_execution import hairpin_request, request_path

CONTROLS = (
    "stem_sequence",
    "endpoint",
    "release_interfaces",
    "open_side_paired_positions",
    "loop_side_paired_bp",
    "terminal_chemistry",
    "non_loop_sequences",
    "regional_contacts",
    "regional_joins",
)


def envelope(tmp_path, endpoint):
    path = hairpin_request(tmp_path) if endpoint == "hairpin" else request_path(tmp_path)
    request = json.loads(path.read_text())
    request["foldback"]["geometry"].update(
        loop_lengths_nt=[3, 4, 6, 8], annealing_arm_lengths_bp=[6, 9, 12]
    )
    request["foldback"]["search"].update(
        max_retained_overhead_nt=32,
        max_search_nodes=100000,
        max_realizations=32,
        result_quota=32,
    )
    path.write_text(json.dumps(request))
    return path


@pytest.fixture(scope="module", params=["hairpin", "insert"])
def explored(request, tmp_path_factory):
    root = tmp_path_factory.mktemp("complete-options-" + request.param)
    path = envelope(root, request.param)
    packet = construction.explore_construction_options(path, max_continuations=12)
    packet.write(root / "options")
    return root, request.param, json.loads(packet.json_bytes)


@pytest.fixture(scope="module", params=["hairpin", "insert"])
def tamper_options(request, tmp_path_factory):
    """Admit a real mixed packet; corruption checks do not need a whole family."""
    root = tmp_path_factory.mktemp("tamper-options-" + request.param)
    path = envelope(root, request.param)
    packet = construction.explore_construction_options(path, max_continuations=2)
    summary = json.loads(packet.json_bytes)
    assert len(summary["candidates"]) == 2
    assert summary["candidates"][0]["status"] == "infeasible"
    assert len(summary["options"]) == 1
    packet.write(root / "options")
    return root, summary


def test_exploration_yields_complete_products_without_a_reference(explored):
    root, endpoint, result = explored
    assert result["coverage"]["recorded_pairs"] == 12
    assert result["coverage"]["evaluated_pairs"] == 12
    assert result["coverage"]["unexamined_pairs"] == 0
    assert result["coverage"]["completion"] == "recorded_pairs_examined"
    assert len(result["options"]) == 11
    assert len(result["candidates"]) == 12
    assert result["candidates"][0]["status"] == "infeasible"
    assert result["candidates"][0]["preparation_constraints"][0]["requested"] == 14
    assert result["selected_options"] == []
    assert (root / "options/report.pdf").read_bytes().startswith(b"%PDF")
    for option in result["options"]:
        assert (root / "options" / option["portrait"]).is_file()
        assert (root / "options" / option["preparation"]).is_file()
        assert option["stage_role"] == ("endpoint" if endpoint == "hairpin" else "intermediate")
    if endpoint == "insert":
        assert result["local_coverage"]["basal"]["termination_reason"] == "result_quota"


def test_selection_uses_visible_labels_and_replays_authorities(explored, tmp_path):
    root, _, result = explored
    label = result["options"][0]["label"]
    selected = construction.select_construction_options(
        root / "options",
        option_labels=(label,),
        baseline=label,
        shared_properties=(),
        compared_properties=(),
    )
    selected.write(tmp_path / "selected")
    actual = json.loads(selected.json_bytes)["members"][0]
    assert (
        actual["materialized_realization_id"] == result["options"][0]["materialized_realization_id"]
    )
    assert (tmp_path / "selected" / actual["preparation"]).is_file()
    assert (tmp_path / "selected/report.pdf").read_bytes().startswith(b"%PDF")
    shutil.move(tmp_path / "selected", tmp_path / "relocated")
    replayed = construction.select_construction_set(tmp_path / "relocated/set.json")
    assert replayed.json_bytes == selected.json_bytes
    with pytest.raises(ValueError, match="Unknown option"):
        construction.select_construction_options(
            root / "options",
            option_labels=("missing",),
            baseline="missing",
            shared_properties=(),
            compared_properties=(),
        )


def test_group_discovery_retains_both_complete_scaffold_backgrounds(explored, tmp_path):
    root, _, result = explored
    request = tmp_path / "comparison.json"
    request.write_text(
        json.dumps(
            {
                "schema": "hop.scaffold-comparison/v1",
                "members": [
                    {"name": f"loop{n}", "dimensions": {"loop_nt": n}} for n in (3, 4, 6, 8)
                ],
                "shared_properties": CONTROLS,
            }
        )
    )
    packet = construction.find_construction_option_sets(root / "options", request)
    summary = json.loads(packet.json_bytes)
    complete = [g for g in summary["groups"] if g["comparison_available"]]
    assert len(complete) == 2
    assert {g["shared_values"]["loop_side_paired_bp"] for g in complete} == {9, 12}
    assert all(len(g["members"]) == 4 and not g["missing_members"] for g in complete)
    assert summary["selected_options"] == []
    assert summary["coverage"] == result["coverage"]
    incomplete = [g for g in summary["groups"] if not g["comparison_available"]]
    assert incomplete[0]["missing_members"] == ["loop3"]
    labels = tuple(m["option_labels"][0] for m in complete[0]["members"])
    selected = construction.select_construction_options(
        root / "options",
        option_labels=labels,
        baseline=labels[0],
        comparison=request,
    )
    selected.write(tmp_path / "controlled-set")
    intent = json.loads((tmp_path / "controlled-set/selected-intent.json").read_bytes())
    assert [m["member"] for m in intent["membership"]] == ["loop3", "loop4", "loop6", "loop8"]
    assert len(json.loads(selected.json_bytes)["members"]) == 4


def test_budget_changes_preserve_product_identity_and_do_not_imply_a_set(explored, tmp_path):
    root, endpoint, full = explored
    if endpoint != "hairpin":
        return
    path = root / "options/inputs/request.json"
    first = construction.explore_construction_options(path, max_continuations=1)
    s = json.loads(first.json_bytes)
    assert not s["options"] and s["coverage"]["unexamined_pairs"] == 11
    assert "larger continuation budget" in first.report_text
    prefix = construction.explore_construction_options(path, max_continuations=6)
    prefix.write(tmp_path / "prefix")
    s = json.loads(prefix.json_bytes)
    assert s["options"] == full["options"][:5]
    assert {o["geometry"]["loop_nt"] for o in s["options"]} == {3, 4, 6, 8}
    comparison = tmp_path / "comparison.json"
    comparison.write_text(
        json.dumps(
            {
                "schema": "hop.scaffold-comparison/v1",
                "shared_properties": CONTROLS,
                "members": [
                    {"name": f"loop{n}", "dimensions": {"loop_nt": n}} for n in (3, 4, 6, 8)
                ],
            }
        )
    )
    grouped = construction.find_construction_option_sets(tmp_path / "prefix", comparison)
    assert json.loads(grouped.json_bytes)["complete_group_count"] == 0
    labels = tuple(
        next(o["label"] for o in s["options"] if o["geometry"]["loop_nt"] == n)
        for n in (3, 4, 6, 8)
    )
    with pytest.raises(ValueError, match="contradicts shared properties"):
        construction.select_construction_options(
            tmp_path / "prefix",
            option_labels=labels,
            baseline=labels[0],
            shared_properties=CONTROLS,
            compared_properties=("loop_nt",),
        )


@pytest.mark.parametrize("edit", ["summary", "request", "projection", "local_authority"])
def test_resealed_edits_do_not_become_molecular_authority(tamper_options, tmp_path, edit):
    root, summary = tamper_options
    source = tmp_path / "edited"
    shutil.copytree(root / "options", source)
    if edit == "summary":
        relative = "summary.json"
        value = json.loads((source / relative).read_bytes())
        value["options"][0]["geometry"]["loop_nt"] = 999
        (source / relative).write_bytes(canonical_json_bytes(value))
    elif edit == "request":
        relative = "inputs/request.json"
        value = json.loads((source / relative).read_bytes())
        value["foldback"]["geometry"]["loop_lengths_nt"] = [4]
        (source / relative).write_bytes(canonical_json_bytes(value))
    elif edit == "local_authority":
        relative = "candidates/0000/outcome/foldback/result.json"
        value = json.loads((source / relative).read_bytes())
        value["result_id"] += "-altered"
        (source / relative).write_bytes(canonical_json_bytes(value))
    else:
        relative = summary["options"][0]["portrait"]
        (source / relative).write_bytes(b"<svg>invented molecule</svg>")
    manifest = json.loads((source / "manifest.json").read_bytes())
    manifest["artifacts"][relative] = sha256_digest((source / relative).read_bytes())
    (source / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="disagrees"):
        construction.select_construction_options(
            source,
            option_labels=(summary["options"][0]["label"],),
            baseline=summary["options"][0]["label"],
            shared_properties=(),
            compared_properties=(),
        )


def test_public_cli_exploration_grouping_and_retrieval(tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = request_path(tmp_path)
    expected = construction.explore_construction_options(path, max_continuations=1)
    output = tmp_path / "cli-options"
    args = ["construction", "explore", str(path), "--max-continuations", "1", "--out", str(output)]
    runner = CliRunner()
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert (output / "summary.json").read_bytes() == expected.json_bytes
    assert runner.invoke(app, args).exit_code != 0
    summary = json.loads(expected.json_bytes)
    label = summary["options"][0]["label"]
    result = runner.invoke(
        app,
        [
            "construction",
            "select-options",
            str(output),
            "--option",
            label,
            "--baseline",
            label,
            "--out",
            str(tmp_path / "selected"),
        ],
    )
    assert result.exit_code == 0, result.output
    selected = json.loads((tmp_path / "selected/summary.json").read_bytes())
    assert (
        selected["members"][0]["materialized_realization_id"]
        == summary["options"][0]["materialized_realization_id"]
    )
    comparison = tmp_path / "comparison.json"
    comparison.write_text(
        json.dumps(
            {
                "schema": "hop.scaffold-comparison/v1",
                "members": [
                    {"name": "loop3", "dimensions": {"loop_nt": 3}},
                    {"name": "loop4", "dimensions": {"loop_nt": 4}},
                ],
                "shared_properties": CONTROLS,
            }
        )
    )
    result = runner.invoke(
        app,
        [
            "construction",
            "option-sets",
            str(output),
            str(comparison),
            "--out",
            str(tmp_path / "groups"),
        ],
    )
    assert result.exit_code == 0, result.output
    groups = json.loads((tmp_path / "groups/summary.json").read_bytes())
    assert groups["complete_group_count"] == 0
    assert groups["groups"][0]["missing_members"] == ["loop3"]
    with pytest.raises((OSError, ValueError)):
        expected.write(path.parent)
    assert path.is_file()


def test_retrieval_reuses_only_this_calls_admitted_candidates(tamper_options, monkeypatch):
    from hop_design.design.construction.complete import bundle as bundles
    from hop_design.design.construction.families import set_members

    root, summary = tamper_options
    original = bundles.load_verified_construction_bundle
    loads = []

    def observed(*args, **kwargs):
        loads.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(bundles, "load_verified_construction_bundle", observed)
    monkeypatch.setattr(set_members, "load_verified_construction_bundle", observed)
    label = summary["options"][0]["label"]
    outputs = []
    for expected_count in (2, 4):
        selected = construction.select_construction_options(
            root / "options", option_labels=(label,), baseline=label
        )
        outputs.append(selected.json_bytes)
        # Each invocation admits the accepted and rejected candidate once.
        # Set assembly binds its selection to that invocation's admitted receipt.
        assert len(loads) == expected_count
    assert outputs[0] == outputs[1]


def test_two_local_domains_retain_actual_pair_coverage(tmp_path):
    path = request_path(tmp_path)
    request = json.loads(path.read_text())
    # A copied-duplex request leaves two basal offsets available; the exact
    # release-interface requirement in the insert seed admits only one.
    request.update(endpoint="hairpin_pcr_duplex", ends=None, release=None)
    request["foldback"]["geometry"]["loop_lengths_nt"] = [4, 6]
    request["foldback"]["search"].update(
        max_realizations=2, result_quota=2, max_retained_overhead_nt=32
    )
    request["basal"]["geometry"]["nick_offsets_nt"] = [0, 1]
    request["basal"]["search"].update(max_realizations=2, result_quota=2)
    path.write_text(json.dumps(request))
    packet = construction.explore_construction_options(path, max_continuations=3)
    summary = json.loads(packet.json_bytes)
    assert summary["local_coverage"]["foldback"]["realization_count"] == 2
    assert summary["local_coverage"]["basal"]["realization_count"] == 2
    assert summary["coverage"]["recorded_pairs"] == 4
    assert summary["coverage"]["evaluated_pairs"] == 3
    assert summary["coverage"]["unexamined_pairs"] == 1
    assert (
        len({tuple(c["selected_local_realizations"].values()) for c in summary["candidates"]}) == 3
    )


def test_options_admission_reuses_exact_local_authorities(tamper_options, monkeypatch):
    from hop_design.design.construction.families import member_admission
    from hop_design.design.construction.options.admission import captured_options

    root, expected = tamper_options
    original = member_admission.load_verified_local_neighborhood
    loads = []

    def observed(*args, **kwargs):
        loads.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(member_admission, "load_verified_local_neighborhood", observed)
    with captured_options(root / "options") as (_, actual, _, _):
        assert actual == expected
    # The enclosing options admission has already verified these exact locals.
    # Each candidate must bind to those bytes without parsing/replaying them again.
    assert loads == []
