"""Request four terminal forms, then explicitly retrieve the demonstrated comparison."""

import argparse
import json
from pathlib import Path

from hop_design import construction


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    template = json.loads(Path(__file__).with_name("terminal-form.json").read_bytes())
    members, observations = [], []
    for name, five, three, paired in (
        ("reference", 6, 14, 18),
        ("short-tail", 6, 8, 18),
        ("no-tail", 6, 0, 18),
        ("paired", 0, 0, 24),
    ):
        request = json.loads(json.dumps(template))
        request["scaffold"] = {
            "five_prime_unpaired_nt": {"minimum": five, "maximum": five},
            "three_prime_unpaired_nt": {"minimum": three, "maximum": three},
        }
        folder = output / name
        folder.mkdir()
        path = folder / "request.json"
        path.write_text(json.dumps(request, indent=2) + "\n")
        construction.prepare_scaffold_discovery(path).write(folder / "preview")
        packet = construction.discover_scaffolds(path)
        packet.write(folder / "options")
        result = json.loads(packet.json_bytes)
        if len(result["options"]) != 1:
            raise ValueError("This prescribed example requires one complete preparation per form.")
        option = result["options"][0]
        if option["geometry"]["open_side_paired_positions"] != paired:
            raise ValueError("Terminal form no longer has the demonstrated paired extent.")
        members.append(
            {
                "name": name,
                **{k: f"{name}/options/{v}" for k, v in option["selection"].items()},
            }
        )
        observations.append(
            {"name": name, "geometry": option["geometry"], "materials": option["material_roles"]}
        )
    reference = observations[0]["materials"]
    for member in observations[1:]:
        changed = {role for role, value in member["materials"].items() if reference[role] != value}
        if changed != {"ligation_adapter"}:
            raise ValueError("The demonstrated family must change only the adapter specification.")
    selection = output / "select.json"
    selection.write_text(
        json.dumps(
            {
                "schema": "hop.construction-set/v1",
                "members": members,
                "baseline": "reference",
                "shared_properties": [
                    "stem_sequence",
                    "loop_nt",
                    "loop_side_paired_bp",
                    "terminal_chemistry",
                ],
                "compared_properties": [
                    "five_prime_unpaired_nt",
                    "three_prime_unpaired_nt",
                    "open_side_paired_positions",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    construction.select_construction_set(selection).write(output / "selected")
    (output / "observations.json").write_text(json.dumps(observations, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
