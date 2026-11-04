"""Route-wide recognition ancestry is prepared once for a complete projection."""

import pytest

from hop_design.design.construction.editions.comparison import captured_route
from hop_design.design.construction.projections import inspection_sites
from hop_design.design.construction.projections.atlas import project_molecular_atlas
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


def test_full_atlas_resolves_recognition_ancestry_once(captured_edition, monkeypatch):  # noqa: F811
    identity = captured_edition.query()["paths"][0]["materialized_realization_id"]
    route = captured_route(captured_edition, identity)
    expected = tuple(
        inspection_sites.inspection_recognition_sites(route, state, {})
        for state in (route.source_preparation.input_state, *route.construction_program.states)
    )
    original = inspection_sites.ancestry_resolver
    calls = []

    def counted(value):
        calls.append(value.materialized_realization_id)
        return original(value)

    monkeypatch.setattr(inspection_sites, "ancestry_resolver", counted)
    atlas = project_molecular_atlas(route)
    assert tuple(state.recognition_sites for state in atlas.states) == expected
    assert calls == [identity], "Build route-wide recognition ancestry once, not once per state"


def test_recognition_index_is_route_local_and_does_not_cache_display_names(captured_edition):  # noqa: F811
    identity = captured_edition.query()["paths"][0]["materialized_realization_id"]
    route = captured_route(captured_edition, identity)
    index = inspection_sites.RecognitionAncestry(route)
    state = route.source_preparation.product_state
    sites = inspection_sites.inspection_recognition_sites(route, state, {}, ancestry=index)
    names = {site.enzyme_id: f"Named {i}" for i, site in enumerate(sites)}
    renamed = inspection_sites.inspection_recognition_sites(route, state, names, ancestry=index)
    assert sites and all(site.enzyme_name == names[site.enzyme_id] for site in renamed)
    assert [s.model_dump(exclude={"enzyme_name"}) for s in sites] == [
        s.model_dump(exclude={"enzyme_name"}) for s in renamed
    ]
    with pytest.raises(ValueError, match="another route"):
        inspection_sites.inspection_recognition_sites(
            route.model_copy(deep=True), state, {}, ancestry=index
        )
