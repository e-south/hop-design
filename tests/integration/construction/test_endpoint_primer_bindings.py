"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/construction/test_endpoint_primer_bindings.py

Checks endpoint primer spans against their named five-prime template strands.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest
import yaml

import hop_design as hop
from hop_design import construction
from hop_design.models.construction.complete import ConstructionState, PrimerExtensionAuthority
from hop_design.models.construction.complete.pcr.replay import validate_pcr_transition
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.sequence import reverse_complement_iupac


@pytest.fixture(scope="module", params=("", "GCT"), ids=("annealing-only", "with-five-prime-tails"))
def primer_extension(tmp_path_factory, request):
    root = Path(__file__).parents[3]
    target = tmp_path_factory.mktemp("endpoint-primer-bindings")
    design = hop.compile(hop.load_spec(root / "examples/construction-exact-design.yaml"))
    design_path = design.write(target / "design")
    source = yaml.safe_load((root / "examples/construction-composed-pcr.yaml").read_text())
    for name in ("forward_primer", "reverse_primer"):
        source["composition"]["materialization"]["endpoint_auxiliaries"][name] = {
            "mode": "constrain",
            "min_annealing_length_nt": 4,
            "max_annealing_length_nt": 4,
            "five_prime_handle_sequence": request.param,
        }
    source_path = target / "request.json"
    source_path.write_text(json.dumps(source))
    result = construction.compile_construction(source_path, design_bundle_path=design_path)
    assert result.status == "complete" and result.valid_realizations > 0
    verified = construction.load_verified_construction_bundle(result.write(target / "construction"))
    projection = construction.project_construction_trajectory(
        verified, materialized_realization_id=verified.materialized_realization_ids[0]
    )
    program = json.loads(projection.json_bytes)["realization"]["construction_program"]
    return (
        PrimerExtensionAuthority.model_validate_json(
            json.dumps(program["transitions"][-1]["pcr_authority"])
        ),
        ConstructionState.model_validate_json(json.dumps(program["states"][-2])),
        ConstructionState.model_validate_json(json.dumps(program["states"][-1])),
    )


def test_endpoint_primer_spans_bind_the_named_template_sequence(primer_extension):
    authority, pre_state, _ = primer_extension
    (hairpin,) = pre_state.molecules
    templates = {
        hairpin.strand_id: hairpin.sequence,
        f"{hairpin.strand_id}-derived-complement": reverse_complement_iupac(hairpin.sequence),
    }
    for binding, primer in zip(
        authority.bindings, (authority.forward_primer, authority.reverse_primer), strict=True
    ):
        template = templates[binding.template_strand_id]
        start, end = binding.template_span.start.offset, binding.template_span.end.offset
        assert 0 <= start < end <= len(template)
        assert reverse_complement_iupac(template[start:end]) == primer.annealing_sequence


def test_resealed_forward_binding_at_the_wrong_template_end_is_rejected(primer_extension):
    authority, pre_state, post_state = primer_extension
    forward, reverse = authority.bindings
    wrong = forward.model_copy(
        update={
            "template_span": Span(
                start=Boundary(offset=0),
                end=Boundary(offset=authority.forward_primer.annealing_length_nt),
            )
        }
    )
    content = {name: value for name, value in authority if name != "authority_id"}
    content["bindings"] = (wrong, reverse)
    forged = PrimerExtensionAuthority.create(**content)
    with pytest.raises(ValueError, match=r"primer bindings.*template boundaries"):
        validate_pcr_transition(
            kind="primer_extension", authority=forged, pre_state=pre_state, post_state=post_state
        )
