"""Primer explanations retain source geometry and the scope of the failed continuation."""

import json
from pathlib import Path

from hop_design import construction
from tests.integration.test_request_execution import hairpin_request


def test_failed_primer_boundary_is_source_geometry_not_a_completed_molecule(tmp_path):
    from hop_design.design.construction.projections.primer_boundary import primer_boundaries

    path = hairpin_request(tmp_path)
    request = json.loads(path.read_bytes())
    request["materialization"]["source_preparation"]["forward_primer"]["annealing_length_nt"] = 20
    path.write_text(json.dumps(request))
    outcome = construction.execute_construction_request(
        path, design_id="primer-boundary", continuation="sole-witness"
    )
    outcome.write(tmp_path / "failed")
    result = json.loads((tmp_path / "failed/construction/construction-result.json").read_bytes())
    (boundary,) = primer_boundaries(result)
    assert boundary["status"] == "rejected_continuation"
    assert boundary["scope"] == "examined_source_geometry_only"
    assert boundary["primer"] == "forward"
    assert boundary["required_nt"] == 20
    assert boundary["available_nt"] == 10
    assert boundary["available_span"] == [0, 10]
    assert boundary["required_span"] == [0, 20]
    assert boundary["stem_span"][0] == 10
    assert len(boundary["source_sequence"][:10]) == boundary["available_nt"]
    assert "molecule_id" not in boundary
    assert "states" not in boundary


def test_complete_options_expose_required_and_available_spans(loop_pool):
    choices = json.loads(
        construction.query_scaffold_variants(
            loop_pool,
            {
                "result_digest": loop_pool.result_digest,
                "stage": "hairpin",
                "focus": "loop",
            },
        ).json_bytes
    )
    space = choices["choice_space"]
    axes = {a["key"]: a for a in space["axes"]}
    for direction in ("forward", "reverse"):
        key = f"source_{direction}_primer_required_nt"
        assert axes[key]["fixed_by_request"] is True
        assert axes[key]["role"] == "required"
        for path in space["paths"]:
            assert path["values"][key] <= path["values"][f"source_{direction}_primer_available_nt"]
    assert all(
        p["values"]["adapter_annealing_achieved_nt"] >= p["values"]["adapter_annealing_min_nt"]
        for p in space["paths"]
    )


def test_choices_carry_scoped_primer_failures_into_portable_report(tmp_path):
    value = json.loads(Path("examples/molecular-editing/request.json").read_bytes())
    value["product"]["foldback"]["geometry"]["loop_sequences"] = ["GAAA"]
    value["product"]["materialization"]["source_preparation"]["reverse_primer"][
        "annealing_length_nt"
    ] = 100
    request = tmp_path / "request.json"
    request.write_text(json.dumps(value))
    saved = construction.discover_scaffolds(request).write(tmp_path / "evaluated")
    pool = construction.load_scaffold_exploration(saved)
    choices = construction.query_scaffold_variants(
        pool,
        {
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
        },
    )
    facts = json.loads(choices.json_bytes)
    assert not facts["compatible_options"]
    rows = facts["choice_space"]["primer_boundaries"]
    assert rows and all(row["required_nt"] == 100 for row in rows)
    assert all(row["available_nt"] < row["required_nt"] for row in rows)
    assert "100 nt required" in choices.report_text
    choices.write(tmp_path / "choices")
    assert b"Examined source" in (tmp_path / "choices/primer-boundaries.svg").read_bytes()
    from typer.testing import CliRunner

    from hop_design.cli import app

    cli = CliRunner().invoke(
        app,
        [
            "construction",
            "variants",
            str(saved),
            "--stage",
            "hairpin",
            "--focus",
            "loop",
            "--out",
            str(tmp_path / "cli-choices"),
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert "100 nt required" in cli.output
    assert json.loads((tmp_path / "cli-choices/summary.json").read_bytes()) == facts
    assert (tmp_path / "cli-choices/primer-boundaries.svg").read_bytes() == (
        tmp_path / "choices/primer-boundaries.svg"
    ).read_bytes()


def test_zero_boundaries_and_primer_thresholds_are_located_on_exact_atlas(loop_pool):
    choices = construction.query_scaffold_variants(
        loop_pool,
        {
            "result_digest": loop_pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
        },
    )
    summary = json.loads(choices.json_bytes)
    atlas = construction.inspect_scaffold_atlas(
        loop_pool,
        choices,
        {
            "result_digest": loop_pool.result_digest,
            "query_digest": summary["query_digest"],
            "option_label": summary["compatible_options"][0],
        },
    )
    data = json.loads(atlas.json_bytes)
    locations = {p["key"]: p for p in data["parameter_locations"]}
    zero = locations["basal_nick_offset_nt"]
    assert zero["zero_extent"]
    assert zero["boundary_anchors"][0]["start"] == zero["boundary_anchors"][0]["end"]
    required = locations["source_reverse_primer_required_nt"]
    available = locations["source_reverse_primer_available_nt"]
    assert required["definition"]["representation"] == "threshold"
    assert len(required["reference_addresses"]) <= len(available["reference_addresses"])
    assert len(locations["adapter_annealing_min_nt"]["reference_addresses"]) <= len(
        locations["adapter_annealing_achieved_nt"]["reference_addresses"]
    )
    assert b'data-parameter-boundary="basal_nick_offset_nt"' in atlas.svg_bytes
