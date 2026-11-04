"""Batched failures retain the exact release permission attempted at each address."""

import json

from hop_design import construction
from tests.integration.test_survey_admission_batching import request_path


def test_inspection_labels_each_skipped_projection_without_modifying_checkpoint(tmp_path):
    path = request_path(tmp_path)
    document = json.loads(path.read_text())
    document["placements"] = [{"left_bp": 0, "right_bp": 0}]
    document["release"]["basal_projections"] = [
        {"product_end": "right", "recognition_material": owner}
        for owner in ("source_duplex", "endpoint_material")
    ]
    path.write_text(json.dumps(document))
    index = tmp_path / "index.sqlite"
    construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=1,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
        continuation_batch_size=8,
    )
    before = index.read_bytes()
    report = construction.inspect_interface_survey(path, index)
    row = report["evaluations"][0]
    assert row["skipped_empty"]
    attempts = [*row["skipped_empty"], row]
    assert {a["basal_release_projection"]["recognition_material"] for a in attempts} == {
        "source_duplex",
        "endpoint_material",
    }
    assert all(a["basal_release_projection"]["product_end"] == "right" for a in attempts)
    assert index.read_bytes() == before
