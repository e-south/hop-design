"""Verify every required exact member before ordinary portable-set assembly."""

import json
import tempfile
from contextlib import ExitStack
from pathlib import Path

from hop_design.models.construction.family.selection import ConstructionSetRequest
from hop_design.serialization import canonical_json_bytes

from ..discovery.admission import captured_discovery
from ..discovery.prepare import prepare_scaffold_discovery
from ..edits.drawings import sequence_drawings
from ..families.selection import ConstructionSet, _select_admitted_construction_set
from ..packets.capture import capture_packet, write_snapshot
from .prepare import prepare_sequence_family
from .records import family_summary


def select_sequence_family(
    path: str | Path, *, members: dict[str, str], baseline: str
) -> ConstructionSet:
    protected, files = capture_packet(path, schema="hop.sequence-family-result-packet/v1")
    with (
        tempfile.TemporaryDirectory(prefix="hop-sequence-selection-") as temporary,
        ExitStack() as stack,
    ):
        root = Path(temporary)
        write_snapshot(files, root)
        prepared = prepare_sequence_family(root / "intent/request.json")
        preview = json.loads(prepared.json_bytes)
        if set(members) != {m["name"] for m in preview["members"]}:
            raise ValueError(
                "Select exactly one option for every required member; "
                "missing members remain unresolved."
            )
        for name, content in prepared._files:
            if files.get("intent/" + name) != content:
                raise ValueError("Saved sequence-family preview differs from the authored domain.")
        records, receipts, producers = {}, {}, []
        for member in preview["members"]:
            name = member["name"]
            local = prepare_scaffold_discovery(root / "intent" / member["request"])
            local_preview = json.loads(local.json_bytes)
            if local_preview["status"] != "ready":
                raise ValueError(f"Required member {name} has conflicting permissions.")
            directory = root / "members" / name
            captured = stack.enter_context(captured_discovery(directory))
            _, native, admitted, _ = captured
            if (directory / "intent/request.json").read_bytes() != dict(prepared._files)[
                member["request"]
            ]:
                raise ValueError("Saved exact member differs from its required stem request.")
            records[name] = native
            producers.append(native["producer"])
            receipts.update({f"{name}-{label}": receipt for label, receipt in admitted.items()})
        if any(p != producers[0] for p in producers):
            raise ValueError("Exact family members must share a producing implementation.")
        summary = family_summary(preview, records, producers[0])
        if canonical_json_bytes(summary) != files["summary.json"]:
            raise ValueError("Saved sequence family differs from verified required members.")
        expected, _ = sequence_drawings(root, summary, receipts)
        if {k: v for k, v in files.items() if k.startswith("views/")} != expected:
            raise ValueError("Saved sequence view differs from verified family molecules.")
        options = {o["label"]: o for o in summary["options"]}
        roster = []
        for name, label in members.items():
            if label not in options or options[label]["member"] != name:
                raise ValueError(f"Select a complete option belonging to required member {name}.")
            roster.append({"name": name, **options[label]["selection"]})
        value = {
            "schema": "hop.construction-set/v2",
            "members": roster,
            "baseline": baseline,
            "shared_properties": preview["shared_properties"],
            "compared_properties": [],
        }
        if baseline not in members:
            raise ValueError("The comparison reference must be an explicitly selected member.")
        if preview["shared_material_roles"]:
            value["reuse_prior_materials"] = {
                "reference": options[members[baseline]]["selection"],
                "roles": preview["shared_material_roles"],
            }
        request = ConstructionSetRequest.model_validate_json(json.dumps(value))
        selected = _select_admitted_construction_set(
            root / "set.json",
            request,
            {name: receipts[label] for name, label in members.items()},
            (protected,),
        )
    output = dict(selected._files)
    output["sequence-family.json"] = files["intent/request.json"]
    output["family-selection.json"] = canonical_json_bytes(
        {"request_digest": preview["request_digest"], "members": members, "baseline": baseline}
    )
    result = ConstructionSet._create(output, json.loads(selected.json_bytes), selected.report_text)
    object.__setattr__(result, "_roots", (protected,))
    return result
