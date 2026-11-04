"""One explicit brief reaches portable named preparations through CLI and Python."""

import json
import shutil
from collections import Counter

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_comparison_assessment import comparison
from tests.integration.test_scaffold_discovery import discovery_request


@pytest.fixture(scope="module")
def executed(tmp_path_factory):
    root = tmp_path_factory.mktemp("comparison-journey")
    discovery = json.loads(discovery_request(root).read_bytes())
    discovery["product"]["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4]
    brief = comparison(
        root,
        discovery,
        members=[{"name": f"loop{n}", "dimensions": {"loop_nt": n}} for n in (3, 4)],
    )
    packet = construction.execute_scaffold_comparison(brief)
    return brief, packet.write(root / "result"), json.loads(packet.json_bytes)


def test_named_set_retrieval_is_explicit_and_portable(executed, tmp_path):
    brief, result, summary = executed
    assert summary["status"] == "comparison_available"
    assert summary["selected_set"] is None
    relocated = tmp_path / "relocated"
    shutil.copytree(result, relocated)
    selected = construction.select_scaffold_comparison(
        relocated, set_label="set-0001", baseline="loop3"
    )
    output = selected.write(tmp_path / "selected")
    members = json.loads(selected.json_bytes)["members"]
    assert [m["name"] for m in members] == ["loop3", "loop4"]
    assert "loop4" in (output / "oligo-uses.csv").read_text()
    assert (
        construction.select_construction_set(output / "set.json").json_bytes == selected.json_bytes
    )
    with pytest.raises(ValueError, match="Unknown comparison set"):
        construction.select_scaffold_comparison(relocated, set_label="set-9999", baseline="loop3")
    runner = CliRunner()
    assessed = runner.invoke(
        app,
        [
            "construction",
            "assess-comparison",
            str(brief),
            str(relocated / "discovery"),
            "--out",
            str(tmp_path / "assessment"),
        ],
    )
    assert assessed.exit_code == 0, assessed.output
    assert json.loads((tmp_path / "assessment/summary.json").read_bytes()) == summary
    chosen = runner.invoke(
        app,
        [
            "construction",
            "select-comparison",
            str(relocated),
            "--set",
            "set-0001",
            "--baseline",
            "loop3",
            "--out",
            str(tmp_path / "cli-selected"),
        ],
    )
    assert chosen.exit_code == 0, chosen.output
    assert (tmp_path / "cli-selected/summary.json").read_bytes() == selected.json_bytes


def test_comparison_sheet_uses_verified_molecules_and_countable_loops(executed):
    _, result, _ = executed
    assert (result / "report.pdf").read_bytes().startswith(b"%PDF")
    page = (result / "pages/comparison-1.svg").read_text()
    assert 'data-comparison-purpose="distinct_substrates"' in page
    assert "data-loop-index=" in page
    assert "loop3" in page and "loop4" in page
    assert "No membership selected" in page


def test_retrieval_admits_discovery_once_per_independent_call(executed, monkeypatch):
    from hop_design.design.construction.comparisons import selection as comparison_selection
    from hop_design.design.construction.complete import bundle
    from hop_design.design.construction.discovery import selection as scaffold_selection

    _, result, _ = executed
    original = comparison_selection.captured_discovery
    admissions = []
    replays = []
    replay = bundle.verify_construction_space_result

    def observed_replay(result, *args, **kwargs):
        replays.append(result.result_id)
        return replay(result, *args, **kwargs)

    monkeypatch.setattr(bundle, "verify_construction_space_result", observed_replay)

    def observed(*args, **kwargs):
        admissions.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(comparison_selection, "captured_discovery", observed)
    monkeypatch.setattr(scaffold_selection, "captured_discovery", observed)
    first = construction.select_scaffold_comparison(result, set_label="set-0001", baseline="loop3")
    assert len(admissions) == 1
    first_replays = Counter(replays)
    assert first_replays and set(first_replays.values()) == {1}
    second = construction.select_scaffold_comparison(result, set_label="set-0001", baseline="loop3")
    assert len(admissions) == 2
    assert Counter(replays) == Counter(dict.fromkeys(first_replays, 2))
    assert first.json_bytes == second.json_bytes
    assert first._files == second._files


def test_resealed_comparison_cannot_invent_membership(executed, tmp_path):
    _, result, _ = executed
    path = tmp_path / "edited"
    shutil.copytree(result, path)
    summary = json.loads((path / "summary.json").read_bytes())
    summary["sets"][0]["members"]["loop4"] = summary["sets"][0]["members"]["loop3"]
    (path / "summary.json").write_bytes(canonical_json_bytes(summary))
    manifest = json.loads((path / "manifest.json").read_bytes())
    manifest["artifacts"]["summary.json"] = sha256_digest((path / "summary.json").read_bytes())
    (path / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match=r"comparison.*disagrees"):
        construction.select_scaffold_comparison(path, set_label="set-0001", baseline="loop3")


def test_tight_discovery_keeps_missing_requested_member(tmp_path):
    discovery = json.loads(discovery_request(tmp_path).read_bytes())
    discovery["max_continuations_per_branch"] = 1
    brief = comparison(
        tmp_path,
        discovery,
        members=[{"name": f"loop{n}", "dimensions": {"loop_nt": n}} for n in (3, 4)],
    )
    packet = construction.execute_scaffold_comparison(brief)
    summary = json.loads(packet.json_bytes)
    assert summary["sets"] == []
    assert [m["name"] for m in summary["members"]] == ["loop3", "loop4"]
    assert summary["members"][1]["status"] == "missing_from_evaluated_pool"
    assert summary["coverage"]["unexamined_pairs"] == 3


def test_conflicting_brief_retains_obligations_without_search(tmp_path):
    discovery = json.loads(discovery_request(tmp_path).read_bytes())
    brief = comparison(
        tmp_path, discovery, members=[{"name": "loop5", "dimensions": {"loop_nt": 5}}]
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["construction", "execute-comparison", str(brief), "--out", str(tmp_path / "conflict")]
    )
    assert result.exit_code == 0, result.output
    summary = json.loads((tmp_path / "conflict/summary.json").read_bytes())
    assert summary["status"] == "conflicting_requirements"
    assert summary["execution"] == "not_started"
    assert summary["members"][0]["name"] == "loop5"
    assert not (tmp_path / "conflict/discovery").exists()


def test_selected_comparison_uses_the_explicit_presentation_baseline(executed, tmp_path):
    _, result, _ = executed
    selected = construction.select_scaffold_comparison(
        result, set_label="set-0001", baseline="loop4"
    ).write(tmp_path / "loop4-reference")
    page = (selected / "comparison/pages/comparison-1.svg").read_text()
    assert "Preparation changes relative to loop4" in page
    assert json.loads((selected / "summary.json").read_bytes())["baseline"] == "loop4"
