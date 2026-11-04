"""Contact endpoint roles cannot erase a recorded noncanonical atlas location."""

from hop_design.design.construction.projections import parameter_locations as locations_module
from hop_design.design.construction.projections.atlas import project_molecular_atlas
from hop_design.design.construction.projections.parameter_teaching import parameter_teaching
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.targets import BasalPairAllowance
from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _construction_request,
    _discover_raw,
    _material,
)
from tests.integration.test_complete_construction_pcr import (
    _foldback,
    _payload,
    _verified_distal_mismatch_design,
)


def test_reversed_contact_endpoints_keep_both_base_locations_and_teaching(tmp_path, monkeypatch):
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
        pairing_allowances=(
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MISMATCH,
            BasalPairAllowance.MATCH,
        ),
        recognition_pattern="TGTC",
        cut_offset_reference_strand=4,
    )
    design = _verified_distal_mismatch_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        adapter=_material("ligation-adapter", basal.realizations[0].proximal_adapter_sequence),
        forward_primer=_material("forward-primer", encoding[:4]),
        reverse_primer=_material("reverse-primer", reverse_complement_iupac(encoding[-1:])),
    )
    route = _discover_raw(request, foldback=foldback, basal=basal, design=design).realizations[0]
    original = route.model_dump_json()
    anatomy = describe_hairpin(route)
    assert anatomy.noncanonical_open_side_contacts == 1
    pair = next(p for p in anatomy.state.pairings if p.kind.value != "watson_crick")
    # Change only the endpoint-role convention supplied to this projection seam.
    # Bases, contacts, state addresses and original complete-route evidence stay fixed.
    reversed_pair = pair.model_copy(
        update={
            "left_index": pair.right_index,
            "right_index": pair.left_index,
            "left_base": pair.right_base,
            "right_base": pair.left_base,
            "left_strand_id": pair.right_strand_id,
            "right_strand_id": pair.left_strand_id,
        }
    )
    state = anatomy.state.model_copy(
        update={
            "pairings": tuple(reversed_pair if p == pair else p for p in anatomy.state.pairings)
        }
    )
    monkeypatch.setattr(
        locations_module, "describe_hairpin", lambda _: anatomy.model_copy(update={"state": state})
    )
    atlas = project_molecular_atlas(route)
    locations = locations_module.parameter_locations(route, atlas)
    noncanonical = next(p for p in locations if p["key"] == "noncanonical_pairs")
    assert {(p["strand_id"], p["index"]) for p in noncanonical["reference_addresses"]} == {
        (pair.left_strand_id, pair.left_index),
        (pair.right_strand_id, pair.right_index),
    }
    teaching = parameter_teaching(
        route,
        atlas,
        locations,
        {"noncanonical_pairs": 1},
        [
            {
                "key": "noncanonical_pairs",
                "values": [{"value": 1, "label": "1"}],
                "declared": {},
                "fixed_by_request": False,
                "observed_variation": False,
            }
        ],
        {},
    )
    assert teaching["parameters"][0]["coverage"] == "located"
    assert route.model_dump_json() == original
