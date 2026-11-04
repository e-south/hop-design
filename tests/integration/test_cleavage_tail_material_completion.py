"""Later primer binding can reject one local completion without losing the next."""

import json

from hop_design import construction
from hop_design.design.construction.foldback_space import discover_sequence_space
from hop_design.design.construction.surveys.foldback_population import FoldbackPopulation
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes
from tests.contract.test_foldback_cleavage_tail import tail_case, tail_request
from tests.integration.test_complete_construction_discovery import _material
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def test_rejected_first_tail_does_not_hide_a_complete_preparation(tmp_path):
    request = tail_request()
    data = _two_method_product().model_dump(mode="json", by_alias=True)
    data.update(stem_arm="GCGC", endpoint="ssdna_hairpin", basal=None, ends=None, release=None)
    data["hairpin_basal_component"] = {"left_arm": "CGCGCGCGCG", "right_arm": "CGCGCGCGCG"}
    data["enzyme_catalog"] = request.enzyme_provisioning.catalog.model_dump(
        mode="json", by_alias=True
    )
    data["foldback"]["geometry"] = request.geometry_domain.model_dump(mode="json")
    data["foldback"]["enzymes"] = request.enzyme_provisioning.model_dump(
        mode="json", exclude={"catalog"}
    )
    data["materialization"]["endpoint_auxiliaries"] = None
    data["materialization"]["source_preparation"] = {
        "source_ssdna": {
            "mode": "derive",
            "five_prime_end": "hydroxyl",
            "three_prime_end": "hydroxyl",
        },
        "forward_primer": {"mode": "derive", "annealing_length_nt": 1},
        "reverse_primer": {
            "mode": "fixed",
            "primer": {
                "oligo": _material(
                    "source-reverse", "GTACGA", five_prime_end=EndChemistry.HYDROXYL
                ).model_dump(mode="json"),
                "annealing_length_nt": 6,
            },
        },
    }
    product = ProductRequest.model_validate_json(json.dumps(data))
    population = FoldbackPopulation(discover_sequence_space(request))
    domain, _, _, kind = tail_case()
    # Both tails pass local cleavage. Only TCGTAC binds the specified source primer.
    outcomes = []
    for tail_word in ("AAG", "CGT"):
        solution = domain.materialize("AAAAAA" + tail_word)
        assert solution.source_reference_sequence.endswith("T" + tail_word + "AC")
        rank = population.ranks_of(solution, program_kind=kind)[0]
        selected = population.select(product, rank)
        root = tmp_path / tail_word
        root.mkdir()
        path = root / "product.json"
        path.write_bytes(canonical_json_bytes(selected))
        construction.prepare_construction_request(path).write(root / "inputs")
        local = construction.discover_local_neighborhood(root / "inputs/foldback.json")
        local.write(root / "foldback")
        record = next(
            r
            for r in json.loads(local.json_bytes)["realizations"]
            if r["source_reference_sequence"] == solution.source_reference_sequence
            and r["program_kind"] == kind.value
        )
        result = construction.continue_construction_request(
            path,
            design_id="tail-completion-" + tail_word.lower(),
            foldback_path=root / "foldback/result.json",
            foldback_realization_id=record["foldback_realization_id"],
        )
        result.write(root / "complete")
        summary = json.loads(result.json_bytes)
        outcomes.append(summary["accepted"])
        if tail_word == "CGT":
            verified = construction.load_verified_construction_bundle(
                root / "complete/construction"
            )
            assert verified.materialized_realization_ids
            assert reverse_complement_iupac(solution.source_reference_sequence[-6:]) == "GTACGA"
    assert outcomes == [0, 1]
