"""Exercise the public survey seam; this narrow fixture is not a scientific survey."""

import argparse
import json
import tempfile
from hashlib import sha256
from pathlib import Path

from hop_design import construction


def run(content_root: Path, output: Path) -> dict:
    seed = json.loads(
        (content_root / "examples/complete-construction/product-request.json").read_text()
    )
    ends = seed.pop("ends")
    seed.update(
        schema="hop.interface-survey/v2", targets={}, placements=[{"left_bp": 6, "right_bp": 6}]
    )
    for key in ("endpoint", "enumeration"):
        seed.pop(key)
    seed["interfaces"] = {
        side: {k: ends[side][k] for k in ("orientation", "overhang_end")}
        for side in ("left", "right")
    }
    for family in ("foldback", "basal"):
        seed[family]["max_retained_overhead_nt"] = seed[family].pop("search")[
            "max_retained_overhead_nt"
        ]
    seed["basal"]["geometry"].pop("minimum_adapter_annealing_nt")
    seed["basal"]["annealing_lengths_nt"] = [17]
    seed["release"].pop("max_site_pairs")
    seed["release"]["basal_projections"] = [seed["release"].pop("basal_projection")]
    output.mkdir()
    request = output / "survey.json"
    request.write_text(json.dumps(seed))
    index = output / "survey.sqlite"
    limits = {"local_nodes": 100, "local_realizations": 16, "release_site_pairs": 100}
    first = construction.evaluate_interface_survey(request, index, max_evaluations=12, **limits)
    assert first["evaluations"] == 12
    resumed = construction.evaluate_interface_survey(
        request, index, max_evaluations=53, resume=True, **limits
    )
    assert resumed["evaluations"] == 65
    assert resumed["coverage"]["target_pairs"] == 65536
    inspected = construction.inspect_interface_survey(request, index)
    witness = next(row for row in inspected["evaluations"] if row["witnesses"])
    verified = construction.verify_interface_survey(request, index)
    assert verified["coverage"] == inspected["coverage"]
    pool = construction.load_interface_survey_choices(request, index)
    selection = pool.select(
        target=witness["target"],
        step=witness["step"],
        materialized_realization_id=witness["witnesses"][0],
    )
    selected = construction.retrieve_interface_survey_witness(
        request,
        index,
        selection=selection,
        destination=output / "selected",
    )
    assert selected.valid_realizations == 1
    assert (output / "selected/preparation/oligos.csv").is_file()
    figure = pool.figure(selection=selection)
    figure_path = figure.write(output / "figure")
    assert (figure_path / "figure.pdf").read_bytes().startswith(b"%PDF")
    assert json.loads((figure_path / "selection.json").read_text()) == selection
    result = {
        "figure_svg_digest": sha256((figure_path / "figure.svg").read_bytes()).hexdigest(),
        "figure_pdf_digest": sha256((figure_path / "figure.pdf").read_bytes()).hexdigest(),
        "progress": resumed,
        "verification": verified,
        "selected_witness": witness["witnesses"],
    }
    (output / "acceptance.json").write_text(json.dumps(result, sort_keys=True, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.out is None:
        with tempfile.TemporaryDirectory(prefix="hop-survey-smoke-") as temporary:
            result = run(args.content_root, Path(temporary) / "acceptance")
    else:
        result = run(args.content_root, args.out)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
