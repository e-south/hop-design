"""Known-handle preference reaches the same verified public selection and handoff."""

import csv
import json

from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.support.context_completion import LIMITS, records, request


def test_known_compatible_handle_precedes_failing_canonical_handle_and_replays(tmp_path):
    path = request(tmp_path, "known-handle", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "CWTTGCAGTCGTAC"
    )
    data["preferred_source_contexts"] = ["CTTTGCAGTCGTAC"]
    path.write_text(json.dumps(data))
    index = tmp_path / "api.sqlite"
    answer = construction.evaluate_interface_survey(path, index, max_evaluations=2, **LIMITS)
    assert answer["coverage"]["supported_pairs"] == 1
    assert answer["enumeration_scope"] == "paired_scaffold_completions"
    attempted = records(index)[-1]
    assert attempted["witnesses"] and attempted["group_pair_resolved"]
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 2
    cli = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "evaluate",
            str(path),
            "--index",
            str(tmp_path / "cli.sqlite"),
            "--max-evaluations",
            "2",
            "--local-nodes",
            "100",
            "--local-realizations",
            "100",
            "--release-site-pairs",
            "100",
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.output) == answer
    assert records(tmp_path / "cli.sqlite") == records(index)

    # Optional intent retains this context; it is not a second search API.
    context = {k: v for k, v in data.items() if k not in {"schema", "stem_arm", "targets", "name"}}
    context.update(
        schema="hop.construction-context/v1",
        context_id="known-handles/v1",
        description="Synthetic known source handle.",
        product="released_insert",
    )
    intent = {
        "stem_arm": data["stem_arm"],
        "product": "released_insert",
        "context": context,
        "ends": {"left": "AGTC", "right": "AGTC"},
    }
    resolved = construction.resolve_design_request(intent)
    assert json.loads(resolved.json_bytes)["effective_request"]["preferred_source_contexts"] == [
        "CTTTGCAGTCGTAC"
    ]
    choices = construction.load_interface_survey_choices(path, index)
    selected = choices.sample(seed=0)
    assert selected["materialized_realization_id"] in attempted["witnesses"]
    receipt = construction.retrieve_interface_survey_witness(
        path, index, selection=selected, destination=tmp_path / "handoff"
    )
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids
    assert (tmp_path / "handoff/preparation/oligos.csv").is_file()


def test_failed_noncanonical_preference_falls_back_and_resume_preserves_exact_witness(tmp_path):
    path = request(tmp_path, "failed-preference", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "MWTTGCAGTCGTAC"
    )
    data["preferred_source_contexts"] = ["CATTGCAGTCGTAC"]
    path.write_text(json.dumps(data))
    index = tmp_path / "resume.sqlite"
    first = construction.evaluate_interface_survey(path, index, max_evaluations=2, **LIMITS)
    assert first["coverage"]["unresolved_pairs"] == 1
    assert records(index)[-1]["outcome"]["rejection_reasons"] == ["global-actionable-site-conflict"]
    assert not records(index)[-1]["group_pair_resolved"]
    resumed = construction.evaluate_interface_survey(
        path, index, max_evaluations=2, resume=True, **LIMITS
    )
    assert resumed["coverage"]["supported_pairs"] == 1
    full = tmp_path / "full.sqlite"
    construction.evaluate_interface_survey(path, full, max_evaluations=4, **LIMITS)
    assert records(index) == records(full)
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 4


def test_handle_seed_repairs_active_site_and_retains_public_resume_and_handoff(tmp_path):
    path = request(tmp_path, "seeded-handle", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "MWTTGCAGTCGTAC"
    )
    data["source_handle_seed"] = "CATTGCAGTCGTAC"
    path.write_text(json.dumps(data))
    context = {k: v for k, v in data.items() if k not in {"schema", "stem_arm", "targets", "name"}}
    context.update(
        schema="hop.construction-context/v1",
        context_id="seeded-handles/v1",
        description="Synthetic reusable source handle.",
        product="released_insert",
    )
    intent = {
        "stem_arm": data["stem_arm"],
        "product": "released_insert",
        "context": context,
        "ends": {"left": "AGTC", "right": "AGTC"},
    }
    resolved = construction.resolve_design_request(intent)
    assert (
        json.loads(resolved.json_bytes)["effective_request"]["source_handle_seed"]
        == data["source_handle_seed"]
    )
    index = tmp_path / "resume.sqlite"
    construction.evaluate_interface_survey(path, index, max_evaluations=2, **LIMITS)
    assert records(index)[-1]["outcome"]["rejection_reasons"] == ["global-actionable-site-conflict"]
    resumed = construction.evaluate_interface_survey(
        path, index, max_evaluations=2, resume=True, **LIMITS
    )
    assert resumed["coverage"]["supported_pairs"] == 1
    full = tmp_path / "full.sqlite"
    cli = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "evaluate",
            str(path),
            "--index",
            str(full),
            "--max-evaluations",
            "4",
            "--local-nodes",
            "100",
            "--local-realizations",
            "100",
            "--release-site-pairs",
            "100",
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert records(index) == records(full)
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 4
    choices = construction.load_interface_survey_choices(path, index)
    construction.retrieve_interface_survey_witness(
        path, index, selection=choices.sample(seed=0), destination=tmp_path / "handoff"
    )
    with (tmp_path / "handoff/preparation/oligos.csv").open() as handle:
        oligos = list(csv.DictReader(handle))
    forward = next(
        o for o in oligos if "source_materialization_forward_primer" in o["roles"].split(";")
    )
    # One change breaks the site; equal-distance completions use lexical order.
    assert forward["sequence_5prime"] == "AATTGCAGTCGTAC"


def test_default_insert_context_uses_the_existing_public_handle_as_a_soft_seed():
    resolved = construction.resolve_design_request(
        {"stem_arm": "ACGTCGAT", "product": "released_insert"}
    )
    effective = json.loads(resolved.json_bytes)["effective_request"]
    assert effective["source_handle_seed"] == "ACGTACAGTCGTAC"
    assert (
        effective["materialization"]["source_preparation"]["source_ssdna"][
            "upstream_sequence_spec"
        ]["base_spec"]
        == "N"
    )
