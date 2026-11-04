"""Molecular comparison preserves exact differences and limits of correspondence."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from hop_design import construction
from hop_design.design.construction.projections.atlas import project_molecular_atlas
from hop_design.design.construction.projections.atlas_comparison import compare_route_atlases
from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.atlas_comparison import render_atlas_comparison
from hop_design.models.construction import ConstructionEndpoint
from tests.integration.test_complete_construction_clone import _clone_request
from tests.integration.test_complete_construction_discovery import _discover_raw
from tests.integration.test_complete_construction_projections import _verified_result
from tests.integration.test_construction_family_report import family_capture  # noqa: F401


def test_ambiguous_loop_growth_is_marked_across_states_without_inventing_added_positions(
    family_capture,  # noqa: F811
):
    routes = [
        construction.load_verified_construction_bundle(
            family_capture / f"executed/members/{name}/outcome/construction"
        )
        ._verified_source()
        .result.realizations[0]
        for name in ("loop3", "loop4")
    ]
    comparison = compare_route_atlases(*routes, reference="short", option="long")
    loop = next(r for r in comparison.regions if r.region == "loop")
    assert (loop.reference_sequence, loop.observed_sequence) == ("AAA", "AAAA")
    assert loop.correspondence == "ambiguous_minimum_edit"
    assert not comparison.additions
    assert len(comparison.unresolved_positions) > 4
    atlas = project_molecular_atlas(routes[1])
    svg = ET.fromstring(render_molecular_atlas(atlas, comparison=comparison))
    unresolved = [e for e in svg.iter() if e.attrib.get("data-correspondence") == "unresolved"]
    assert len(unresolved) == len(comparison.unresolved_positions)
    assert not any(e.attrib.get("data-change") == "added" for e in svg.iter())
    details = ET.fromstring(render_atlas_comparison(comparison))
    region = next(e for e in details.iter() if e.attrib.get("data-region-comparison") == "loop")
    assert "AAA" in "".join(region.itertext())
    assert "AAAA" in "".join(region.itertext())
    assert "unresolved" in "".join(region.itertext())


def test_chemistry_change_is_visible_even_when_all_sequences_match(tmp_path):
    request, foldback, basal, design, _, _ = _clone_request(tmp_path)
    data = request.model_dump(mode="json", by_alias=True)
    source = data["materialization"]["source_preparation"]["source_ssdna"]
    source["five_prime_end"] = "phosphate"
    source.pop("material_id", None)
    altered = type(request).model_validate_json(json.dumps(data))
    routes = [
        _discover_raw(r, foldback=foldback, basal=basal, design=design).realizations[0]
        for r in (request, altered)
    ]
    comparison = compare_route_atlases(*routes, reference="original", option="phosphorylated")
    assert not comparison.substitutions
    assert len(comparison.materials) == 1
    material = comparison.materials[0]
    assert material.role == "source_ssdna"
    assert material.reference.sequence_5prime == material.observed.sequence_5prime
    svg = ET.fromstring(
        render_molecular_atlas(project_molecular_atlas(routes[1]), comparison=comparison)
    )
    assert b"Source oligo changed" in ET.tostring(svg)
    details = ET.fromstring(render_atlas_comparison(comparison))
    row = next(
        e for e in details.iter() if e.attrib.get("data-material-comparison") == "source_ssdna"
    )
    text = "".join(row.itertext())
    assert "hydroxyl" in text and "phosphate" in text
    assert text.count(material.reference.sequence_5prime) == 2


def test_comparison_rejects_different_requested_endpoints(tmp_path):
    a, b = [
        _verified_result(tmp_path / name, endpoint).result.realizations[0]
        for name, endpoint in (
            ("hairpin", ConstructionEndpoint.SSDNA_HAIRPIN),
            ("insert", ConstructionEndpoint.CLONE_READY_DUPLEX),
        )
    ]
    with pytest.raises(ValueError, match="same endpoint"):
        compare_route_atlases(a, b, reference="hairpin", option="insert")


def test_unique_loop_addition_follows_recorded_ancestry_into_copied_products(tmp_path):
    from tests.integration.test_construction_family import family_path

    path = family_path(tmp_path)
    base = json.loads(path.read_text())["base_request"]
    routes = []
    for word in ("AAA", "AAAT"):
        base["foldback"]["geometry"].update(
            annealing_arm_lengths_bp=[7], loop_lengths_nt=[len(word)], loop_sequences=[word]
        )
        request = tmp_path / f"{word}.json"
        request.write_text(json.dumps(base))
        output = construction.execute_construction_request(
            request, design_id=f"loop-{word.lower()}", continuation="sole-witness"
        ).write(tmp_path / word)
        routes.append(
            construction.load_verified_construction_bundle(output / "construction")
            ._verified_source()
            .result.realizations[0]
        )
    comparison = compare_route_atlases(*routes, reference="short", option="long")
    loop = next(r for r in comparison.regions if r.region == "loop")
    assert (loop.reference_sequence, loop.observed_sequence) == ("AAA", "AAAT")
    assert loop.correspondence == "unique_minimum_edit"
    assert len(comparison.additions) > 1
    assert not comparison.unresolved_positions
    atlas = project_molecular_atlas(routes[1])
    endpoint = atlas.states[-1]
    added_bases = [b.base for b in endpoint.bases if b.address in comparison.additions]
    assert sorted(added_bases) == ["A", "T"]
    svg = ET.fromstring(render_molecular_atlas(atlas, comparison=comparison))
    assert sum(e.attrib.get("data-change") == "added" for e in svg.iter()) == len(
        comparison.additions
    )


def test_method_change_reveals_retained_substitution_and_exact_materials(tmp_path):
    edit = construction.author_molecular_edit(
        Path("examples/molecular-editing/request.json"),
        end_placements=((6, 6),),
        basal_nick_enzyme_ids=("example:enzyme/nb.bsrdi@1", "example:enzyme/nb.btsi@1"),
    ).write(tmp_path / "edit")
    output = construction.execute_molecular_edit(edit / "edit.json").write(tmp_path / "result")
    pool = construction.load_scaffold_exploration(output)
    routes = [r for _, r in pool._routes]
    comparison = compare_route_atlases(*routes, reference="bsrdi", option="btsi")
    assert comparison.reference_loop == comparison.observed_loop
    assert set(comparison.material_roles) == {"source_ssdna", "ligation_adapter"}
    pairs = {(s.reference_base, s.observed_base) for s in comparison.substitutions}
    assert pairs == {("A", "G"), ("T", "C")}
    assert all(r.reference_sequence != r.observed_sequence for r in comparison.endpoint_regions)
    assert all(
        m.reference.sequence_5prime != m.observed.sequence_5prime for m in comparison.materials
    )
    svg = ET.fromstring(
        render_molecular_atlas(project_molecular_atlas(routes[1]), comparison=comparison)
    )
    assert any(e.get("data-change") == "substitution" for e in svg.iter())
    details = ET.fromstring(render_atlas_comparison(comparison))
    assert {
        e.attrib["data-material-comparison"]
        for e in details.iter()
        if "data-material-comparison" in e.attrib
    } == set(comparison.material_roles)


def test_retained_primer_extension_is_marked_without_changing_hairpin_contacts(tmp_path):
    request, foldback, basal, design, _, encoding = _clone_request(tmp_path)
    data = request.model_dump(mode="python", by_alias=True)
    primer = data["materialization"]["endpoint_auxiliaries"]["forward_primer"]["primer"]["oligo"]
    primer["sequence_5prime"] = "GGTCTCTTCCGG" + encoding[:4]
    del primer["material_id"]
    data["release"]["left"].update(payload_end_offset_bp=6, cohesive_end_sequence="TTCC")
    altered = type(request).model_validate(data)
    routes = [
        _discover_raw(r, foldback=foldback, basal=basal, design=design).realizations[0]
        for r in (request, altered)
    ]
    assert routes[0].basal_authority == routes[1].basal_authority
    comparison = compare_route_atlases(*routes, reference="original", option="extended")
    assert all(r.reference_sequence == r.observed_sequence for r in comparison.regions)
    assert comparison.endpoint_regions[0].correspondence == "unique_minimum_edit"
    assert comparison.endpoint_regions[1].correspondence == "ambiguous_minimum_edit"
    atlas = project_molecular_atlas(routes[1])
    endpoint = atlas.states[-1].state
    first, second = endpoint.molecules
    assert first.sequence.startswith("TTCCGG")
    assert second.sequence.endswith("TTTTCC")
    expected = {(first.strand_id, i) for i in range(6)}
    assert {
        (a.strand_id, a.index) for a in comparison.additions if a.state_id == endpoint.state_id
    } == expected
    earlier = {s.state.state_id for s in atlas.states[:-2]}
    assert not any(a.state_id in earlier for a in comparison.additions)
    assert {
        (a.strand_id, a.index)
        for a in comparison.unresolved_positions
        if a.state_id == endpoint.state_id
    } == {(second.strand_id, i) for i in range(len(second.sequence) - 6, len(second.sequence))}
