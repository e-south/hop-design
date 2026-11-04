"""Rehashed bookkeeping cannot substitute for complete molecular authority."""

import json
import shutil

import pytest

from hop_design import construction
from hop_design.design.construction.surveys.admission import open_survey
from hop_design.design.construction.surveys.execute import load_request
from hop_design.design.runtime import producer_identity
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.support.interface_surveys import survey_selection
from tests.unit.test_interface_survey_request import survey_document


@pytest.fixture(scope="module")
def survey(tmp_path_factory):
    root = tmp_path_factory.mktemp("survey-authority")
    doc = survey_document()
    doc["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    doc["placements"] = [{"left_bp": 6, "right_bp": 6}]
    doc["basal"]["annealing_lengths_nt"] = [17]
    request = root / "request.json"
    request.write_text(json.dumps(doc))
    index = root / "index.sqlite"
    construction.evaluate_interface_survey(
        request,
        index,
        max_evaluations=1,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
    )
    return request, index


def mutate(request, path, change):
    index, _ = open_survey(
        path, request=load_request(request), producer=producer_identity(), read_only=False
    )
    with index:
        record = json.loads(index.record(0, step=0))
        change(record)
        content = canonical_json_bytes(record)
        digest = index.put_object(content)
        row = (
            0,
            0,
            digest,
            len(record["witnesses"]),
            int(record["next"] is None and record["exhaustion_proven"]),
        )
        with index._db:
            index._db.execute(
                "UPDATE steps SET record_digest=?, witness_count=?, exhausted=?, digest=? "
                "WHERE ordinal=0 AND step=0",
                (digest, row[3], row[4], sha256_digest(canonical_json_bytes(row))),
            )


def test_molecular_replay_rejects_rehashed_premature_exhaustion(survey, tmp_path):
    request, source = survey
    path = tmp_path / "tampered.sqlite"
    shutil.copyfile(source, path)
    mutate(request, path, lambda row: row.update(next=None, exhaustion_proven=True))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="molecular replay"):
        construction.verify_interface_survey(request, path)
    assert path.read_bytes() == before


def test_selected_witness_rejects_rehashed_wrong_local_pair_address(survey, tmp_path):
    request, source = survey
    path = tmp_path / "tampered.sqlite"
    shutil.copyfile(source, path)
    mutate(request, path, lambda row: row.update(pair=999))
    with pytest.raises(ValueError, match="pair"):
        construction.retrieve_interface_survey_witness(
            request,
            path,
            selection=survey_selection(request, path, 0, 0),
            destination=tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()


def test_retrieval_from_relocated_index_agrees_and_cannot_overwrite(survey, tmp_path):
    request, source = survey
    path = tmp_path / "relocated.sqlite"
    shutil.copyfile(source, path)
    before = path.read_bytes()
    a = construction.retrieve_interface_survey_witness(
        request, path, selection=survey_selection(request, path, 0, 0), destination=tmp_path / "a"
    )
    b = construction.retrieve_interface_survey_witness(
        request,
        source,
        selection=survey_selection(request, source, 0, 0),
        destination=tmp_path / "b",
    )
    assert a.materialized_realization_ids == b.materialized_realization_ids
    assert (tmp_path / "a/preparation/oligos.csv").read_bytes() == (
        tmp_path / "b/preparation/oligos.csv"
    ).read_bytes()
    assert path.read_bytes() == before
    with pytest.raises(FileExistsError):
        construction.retrieve_interface_survey_witness(
            request,
            path,
            selection=survey_selection(request, path, 0, 0),
            destination=tmp_path / "a",
        )


def test_rehashed_release_permission_cannot_rebind_a_witness_to_another_branch(survey, tmp_path):
    request, source = survey
    path = tmp_path / "tampered-projection.sqlite"
    shutil.copyfile(source, path)
    index, _ = open_survey(
        path, request=load_request(request), producer=producer_identity(), read_only=False
    )
    with index:
        record = json.loads(index.record(0, step=0))
        product = json.loads(index.get_object(record["product_request"]))
        assert product["release"]["basal_projection"]["recognition_material"] == "source_duplex"
        product["release"]["basal_projection"]["recognition_material"] = "endpoint_material"
        changed = index.put_object(canonical_json_bytes(product))
    mutate(request, path, lambda row: row.update(product_request=changed))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="request"):
        construction.retrieve_interface_survey_witness(
            request,
            path,
            selection=survey_selection(request, path, 0, 0),
            destination=tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()
    assert path.read_bytes() == before
