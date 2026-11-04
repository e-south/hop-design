"""Write a bounded joint end-pair request from the public scaffold seed."""

import argparse
import copy
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(Path(__file__).with_name("request.json").read_text())
    pairs = [copy.deepcopy(value["product"]["ends"]) for _ in range(3)]
    pairs[1]["left"]["cohesive_end_sequence"] = "CATT"
    pairs[2]["right"]["cohesive_end_sequence"] = "AGCC"
    value.update(
        schema="hop.scaffold-discovery/v6",
        receiving_end_pairs=pairs,
        max_branches=3,
        max_continuations_per_branch=1,
    )
    value["product"]["foldback"]["geometry"]["loop_lengths_nt"] = [4]
    with args.out.open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
