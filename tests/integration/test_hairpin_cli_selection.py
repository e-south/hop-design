"""Exact direct-hairpin selections remain usable through the public CLI."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_request_execution import hairpin_request


def _arguments(output, foldback, realization_id, *, endpoint="ssdna_hairpin"):
    return [
        "construction",
        "compile-local-design",
        "--design-id",
        "selected-hairpin",
        "--payload",
        "ATAACTTCGTATAGCATACATTATACGAAGTTAT",
        "--endpoint",
        endpoint,
        "--foldback",
        str(foldback),
        "--foldback-realization-id",
        realization_id,
        "--out",
        str(output),
    ]


def test_hairpin_cli_selection_matches_api_and_completes_without_insert(tmp_path: Path):
    request = hairpin_request(tmp_path)
    prepared = construction.prepare_construction_request(request)
    prepared.write(tmp_path / "inputs")
    local = construction.discover_local_neighborhood(tmp_path / "inputs/foldback.json")
    local.write(tmp_path / "foldback")
    selected = construction.list_local_realizations(local)[0].realization_id
    payload = json.loads(request.read_text())["stem_arm"]
    expected = construction.compile_design_from_local_realizations(
        design_id="selected-hairpin",
        payload_sequence=payload,
        endpoint="ssdna_hairpin",
        foldback=local,
        foldback_realization_id=selected,
        hairpin_basal_arms=("AGTCGCAATG", "CATTGCGACT"),
    )
    output = tmp_path / "design"
    arguments = _arguments(output, tmp_path / "foldback/result.json", selected)
    arguments[arguments.index("--payload") + 1] = payload
    result = CliRunner().invoke(
        app, [*arguments, "--hairpin-left-arm", "AGTCGCAATG", "--hairpin-right-arm", "CATTGCGACT"]
    )
    assert result.exit_code == 0, result.output
    assert (output / "hop-plan.json").read_bytes() == expected.artifacts["hop-plan.json"]
    expected.write(tmp_path / "api-design")
    complete = construction.compile_construction_from_local_realizations(
        tmp_path / "inputs/construction.json",
        design_bundle_path=tmp_path / "api-design",
        foldback=local,
        foldback_realization_id=selected,
    )
    selected_result = CliRunner().invoke(
        app,
        [
            "construction",
            "compile-selected",
            str(tmp_path / "inputs/construction.json"),
            "--design-bundle",
            str(output),
            "--foldback",
            str(tmp_path / "foldback/result.json"),
            "--foldback-realization-id",
            selected,
            "--out",
            str(tmp_path / "complete"),
        ],
    )
    assert selected_result.exit_code == 0, selected_result.output
    verified = construction.load_verified_construction_bundle(tmp_path / "complete")
    assert verified.result_id == complete.result_id
    assert verified.status == "complete"
    trajectory = json.loads(
        construction.project_construction_trajectory(
            verified, materialized_realization_id=verified.materialized_realization_ids[0]
        ).json_bytes
    )
    assert [len(s["sequence"]) for s in trajectory["realization"]["final_product"]["strands"]] == [
        104
    ]
    for label, chosen, left, right in (
        ("unknown-selection", "not-an-existing-realization", "AGTCGCAATG", "CATTGCGACT"),
        ("ambiguous-arm", selected, "NGTCGCAATG", "CATTGCGACT"),
        ("unpaired-arms", selected, "AGTCGCAATG", "A"),
    ):
        rejected_output = tmp_path / label
        rejected = CliRunner().invoke(
            app,
            [
                *_arguments(rejected_output, tmp_path / "foldback/result.json", chosen),
                "--hairpin-left-arm",
                left,
                "--hairpin-right-arm",
                right,
            ],
        )
        assert rejected.exit_code == 2, rejected.output
        assert not rejected_output.exists()
        if label == "unknown-selection":
            assert "not found exactly once" in " ".join(rejected.output.split())


@pytest.mark.parametrize(
    "endpoint,arms,basal,message",
    [
        ("ssdna_hairpin", [], [], "requires both"),
        ("ssdna_hairpin", ["--hairpin-left-arm", "AGTC"], [], "requires both"),
        ("ssdna_hairpin", ["--hairpin-right-arm", "GACT"], [], "requires both"),
        (
            "hairpin_pcr_duplex",
            ["--hairpin-left-arm", "AGTC", "--hairpin-right-arm", "GACT"],
            [],
            "only for",
        ),
        ("clone_ready_duplex", ["--hairpin-left-arm", "AGTC"], [], "only for"),
        (
            "ssdna_hairpin",
            ["--hairpin-left-arm", "AGTC", "--hairpin-right-arm", "GACT"],
            ["--basal", "basal.json"],
            "omit basal",
        ),
        (
            "ssdna_hairpin",
            ["--hairpin-left-arm", "AGTC", "--hairpin-right-arm", "GACT"],
            ["--basal-realization-id", "selected"],
            "omit basal",
        ),
    ],
)
def test_invalid_hairpin_cli_contract_rejects_before_loading_or_writing(
    tmp_path, monkeypatch, endpoint, arms, basal, message
):
    def unexpected_load(*args, **kwargs):
        raise AssertionError("Invalid endpoint/arm arguments must reject before local loading")

    monkeypatch.setattr(construction, "load_verified_local_neighborhood", unexpected_load)
    output = tmp_path / "out"
    result = CliRunner().invoke(
        app,
        [
            *_arguments(output, tmp_path / "missing.json", "explicit-id", endpoint=endpoint),
            *arms,
            *basal,
        ],
    )
    assert result.exit_code == 2, result.output
    assert message in " ".join(result.output.split())
    assert not output.exists()
