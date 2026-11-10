"""Reproduce explicit public construction requests through the shared execution API."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from hop_design import api, construction


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def execute_case(root, name, authored):
    request = root / f"{name}-product-request.json"
    write_json(request, authored)
    receipt = construction.execute_construction_request(
        request, design_id="public-journey-" + name, continuation="sole-witness"
    )
    receipt.write(root / name)
    row = json.loads(receipt.json_bytes)
    row["actual_ends"] = {}
    projection = root / name / "handoff/projection.json"
    molecular = None
    if projection.is_file():
        molecular = json.loads(projection.read_text())["realization"]
        row["actual_ends"] = {
            end["product_end"]: end["sequence"]
            for end in molecular["final_product"].get("cohesive_ends", [])
        }
        verified = construction.load_verified_construction_bundle(root / name / "construction")
        construction.project_hairpin_portrait(
            verified, materialized_realization_id=molecular["materialized_realization_id"]
        ).write(root / name / "portrait")
    return row, molecular


def hairpin_request(authored):
    """Author a separate preparation with explicit terminal arms and no insert dependency."""
    hairpin = deepcopy(authored)
    hairpin.update(endpoint="ssdna_hairpin", basal=None, release=None, ends=None)
    hairpin["hairpin_basal_component"] = {"left_arm": "AGTCGCAATG", "right_arm": "CATTGCGACT"}
    hairpin["enzyme_catalog"]["enzymes"] = [
        enzyme
        for enzyme in hairpin["enzyme_catalog"]["enzymes"]
        if enzyme["enzyme_id"] in hairpin["foldback"]["enzymes"]["allowed_enzyme_ids"]
    ]
    hairpin["materialization"].pop("endpoint_auxiliaries", None)
    preparation = hairpin["materialization"]["source_preparation"]
    preparation["source_ssdna"] = {
        "mode": "derive",
        "five_prime_end": "hydroxyl",
        "three_prime_end": "hydroxyl",
    }
    preparation["forward_primer"]["annealing_length_nt"] = 10
    return hairpin


def adapted_requests(authored, reference):
    # These four contact positions are explicitly permitted to be noncanonical.
    edited = deepcopy(authored)
    edited["ends"]["left"]["cohesive_end_sequence"] = "GATC"
    geometry = edited["basal"]["geometry"]
    geometry["max_noncanonical_pairs"] = 4
    for contact in geometry["pairing_constraints"]:
        if 6 <= contact["position_from_ligation"] < 10:
            contact["allowed_class"] = "any"
    fixed = deepcopy(edited)
    fixed["materialization"]["source_preparation"]["source_ssdna"] = {
        "mode": "fixed",
        "material": reference["source_preparation"]["source_ssdna"],
    }
    return fixed, edited


def run(output, case="all"):
    output.mkdir(parents=True, exist_ok=False)
    authored = json.loads(Path(__file__).with_name("product-request.json").read_text())
    producer = api.runtime_identity()
    cases = {}
    if case in {"all", "hairpin"}:
        cases["hairpin"], _ = execute_case(output, "hairpin", hairpin_request(authored))
    if case in {"all", "released"}:
        cases["released"], reference = execute_case(output, "released", authored)
        if case == "all":
            if reference is None:
                for name in ("fixed-source-edit", "redesigned-source-edit"):
                    cases[name] = {
                        "status": "not-evaluated",
                        "reason": "Reference preparation unavailable for the material comparison.",
                    }
            else:
                fixed, edited = adapted_requests(authored, reference)
                cases["fixed-source-edit"], _ = execute_case(output, "fixed-source-edit", fixed)
                cases["redesigned-source-edit"], _ = execute_case(
                    output, "redesigned-source-edit", edited
                )
    if api.runtime_identity() != producer:
        raise ValueError("The executing producer changed during the example.")
    payload_nt = next(row["payload_nt"] for row in cases.values() if "payload_nt" in row)
    write_json(
        output / "summary.json", {"payload_nt": payload_nt, "producer": producer, "cases": cases}
    )
    (output / "README.md").write_text(
        "# Public construction walkthrough\n\n"
        "Read an accepted case's portrait/projection.svg to see the whole hairpin, "
        "then portrait/preparation/oligos.csv and report.md for that exact preparation.\n"
        "summary.json and each case's report.md retain outcomes, including rejections.\n"
        "The local searches stop at one witness; only that selected combination is continued.\n"
        "The fixed-source edit is an expected rejection, not a uniquely diagnosed repair.\n"
        "The independent hairpin case authors its own terminal arms and preparation; "
        "it is not an aliquot of the released-insert preparation.\n"
    )
    write_json(
        output / "manifest.json",
        {
            "recipe_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "request_sha256": sha256(
                Path(__file__).with_name("product-request.json").read_bytes()
            ).hexdigest(),
            "artifacts": {
                p.relative_to(output).as_posix(): sha256(p.read_bytes()).hexdigest()
                for p in sorted(output.rglob("*"))
                if p.is_file()
            },
        },
    )
    print(json.dumps({name: row["status"] for name, row in cases.items()}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--case", choices=("all", "hairpin", "released"), default="all")
    args = parser.parse_args()
    run(args.out, args.case)
