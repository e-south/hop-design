"""A selected trace retains the endpoint-conditioned local page during recovery."""

import hashlib
import json

from hop_design import construction
from tests.unit.test_interface_survey_request import survey_document


def recovery_document():
    data = survey_document()
    catalog = data["enzyme_catalog"]["enzymes"]
    bsr = next(e for e in catalog if e["canonical_name"] == "Nb.BsrDI")
    nick = next(e for e in catalog if e["canonical_name"] == "Nt.Bpu10I")
    release = next(e for e in catalog if e["canonical_name"] == "BsaI-HFv2")
    # The same public enzyme definitions used by the nicking and scaffold tests.
    nick = {
        **nick,
        "enzyme_id": "example:enzyme/nt-cvipii@1",
        "canonical_name": "Nt.CviPII",
        "recognition_pattern": "CCD",
        "recognition_length": 3,
        "cut_offset_reference_strand": 0,
        "vendor_metadata": [],
        "characterization_source": {
            "system": "hop-design",
            "kind": "public-test-fixture",
            "id": "tests/contract/test_nicking_discovery.py",
        },
    }
    release = {
        **release,
        "enzyme_id": "example:enzyme/bbsi-hf@1",
        "canonical_name": "BbsI-HF",
        "recognition_pattern": "GAAGAC",
        "cut_offset_reference_strand": 8,
        "cut_offset_complement_strand": 12,
        "vendor_metadata": [],
        "characterization_source": {
            "system": "hop-design",
            "kind": "public-test-fixture",
            "id": "tests/integration/test_scaffold_discovery.py",
        },
    }
    data["enzyme_catalog"]["enzymes"] = [bsr, nick, release]

    def permissions(names, roles):
        return {
            "allowed_enzyme_ids": names,
            "forbidden_enzyme_ids": [],
            "reserved_enzyme_ids": [],
            "max_operations": 2,
            "role_restrictions": [{"role": role, "allowed_enzyme_ids": ids} for role, ids in roles],
        }

    b, n, r = bsr["enzyme_id"], nick["enzyme_id"], release["enzyme_id"]
    data["foldback"]["enzymes"] = permissions([b], [("foldback_nick", [b])])
    data["basal"]["enzymes"] = permissions(
        [n, b, r], [("basal_nick", [n, b]), ("end_generation", [r])]
    )
    data["release"]["enzymes"] = permissions([r], [("end_generation", [r])])
    data["release"]["basal_projections"] = [
        {"product_end": "right", "recognition_material": "endpoint_material"}
    ]
    data["source_context_objective"] = "paired_scaffold_completions"
    data["targets"] = {"left_words": ["AAAA"], "right_words": ["AAAA"]}
    data["placements"] = [{"left_bp": 0, "right_bp": 0}]
    data["basal"]["annealing_lengths_nt"] = [12]
    data["basal"]["geometry"].update(
        nick_offsets_nt=[4], pairing_constraints=[], max_noncanonical_pairs=4
    )
    data["basal"]["end_footprint_pairing"] = {
        "proximal": "match",
        "reference": "left_end_source_contacts",
        "within": "any",
    }
    data["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[5],
        junction_offsets_nt=[0],
        loop_lengths_nt=[4],
        loop_sequences=["AAAG"],
    )
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "N" * 14
    )
    return data


def test_selected_conditioned_page_opens_the_same_atlas_and_preparation(tmp_path):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(recovery_document()))
    index = tmp_path / "index.sqlite"
    result = construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=4,
        continuation_batch_size=64,
        local_nodes=1000,
        local_realizations=1000,
        release_site_pairs=1000,
    )
    assert result["coverage"]["supported_pairs"] == 1
    before = hashlib.sha256(index.read_bytes()).hexdigest()
    selected = construction.load_interface_survey_choices(path, index).sample(seed=23)
    packet = construction.inspect_interface_survey_atlas(path, index, selection=selected)
    assert json.loads(packet.json_bytes)["selection"] == selected
    receipt = construction.retrieve_interface_survey_witness(
        path, index, selection=selected, destination=tmp_path / "preparation"
    )
    assert receipt.materialized_realization_ids == (selected["materialized_realization_id"],)
    assert hashlib.sha256(index.read_bytes()).hexdigest() == before
