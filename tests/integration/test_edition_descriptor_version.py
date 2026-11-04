"""Older atlas descriptors keep their declared comparison scope on reopening."""

import json
from dataclasses import replace

import pytest

from hop_design.api import _InspectionProjection
from hop_design.design.construction.editions.authority import check_descriptor
from hop_design.design.construction.editions.comparison import captured_route
from hop_design.design.construction.navigation.molecular_descriptor import molecular_descriptor
from tests.integration.test_atlas_edition import captured_choices as captured_choices


def test_legacy_preview_keeps_original_fields_and_current_retention_is_verified(
    captured_choices, tmp_path
):
    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    route = captured_route(edition, identity)
    current = molecular_descriptor(route)
    assert current.retained_terminal_bases is not None
    legacy = current.model_copy(update={"retained_terminal_bases": None})
    check_descriptor(route, legacy)
    check_descriptor(route, current)
    for descriptor in (legacy, current):
        with pytest.raises(ValueError, match="descriptor disagrees"):
            check_descriptor(route, descriptor.model_copy(update={"stem": "AAAA"}))
    wrong_retention = current.model_copy(
        update={"retained_terminal_bases": {"five_prime": ("A",), "three_prime": ("T",)}}
    )
    assert wrong_retention != current
    with pytest.raises(ValueError, match="descriptor disagrees"):
        check_descriptor(route, wrong_retention)

    job = _InspectionProjection.preview_job(edition, identity, answer)
    legacy_job = replace(job, descriptor=json.dumps(legacy.model_dump()).encode())
    assert _InspectionProjection.render_preview_job(legacy_job) == (
        _InspectionProjection.render_preview_job(job)
    )
