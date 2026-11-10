"""Readable access to the complete parameter vocabulary beneath the primary plot."""

from typing import Any

from .layout import node_label


def parameter_guide(key: dict[str, Any]) -> bytes:
    rows = [
        "# Molecular design parameters",
        "",
        "Start with the supplied stem. Constrain the product features that matter to your "
        "experiment; leave other choices open. A complete trace connects choices that work "
        "together in one modeled preparation.",
        "",
        "The teaching strip shows the product features. Construction parameters below explain "
        "how they can be made. Derived measurements describe the result; they are not "
        "independent degrees of freedom. The same API keys work in a CLI query.",
        "",
        "Fixed values in the plot come from declared permissions. A value seen in only one "
        "complete design can still belong to a wider permitted domain. See domains.csv for "
        "the evaluated values and their support; parameter-key.json retains the full domains.",
        "",
    ]
    for parameter in key["parameters"]:
        definition = parameter["definition"]
        name = definition["label"]
        stage = definition["stage"].replace("_", " ")
        rows.extend(
            [
                f"## {name}",
                "",
                f"`{definition['key']}` · {stage} · "
                f"{definition.get('design_role', 'construction')}",
                "",
                definition["measurement"],
                "",
            ]
        )
        if definition.get("relationship"):
            rows.extend([f"Relationship: {definition['relationship']}.", ""])
        equivalent = definition.get("equivalent_measurements", [])
        if equivalent:
            rows.extend(["Same measurement: " + ", ".join(f"`{v}`" for v in equivalent) + ".", ""])
    return ("\n".join(rows)).encode()


def plot_context(
    presentation: dict[str, Any], fully_enumerated: bool, context_count: int
) -> list[tuple[str, dict[str, str]]]:
    """Explain request permissions and observed coverage beneath the shared plot."""
    notes: list[tuple[str, dict[str, str]]] = []
    fixed = [
        f"{a['label']} = {', '.join(node_label(a, n) for n in a['nodes']) or 'see request'}"
        for a in presentation["fixed"]
        if a.get("design_role") == "product" or a["representation"] in ("recognition", "threshold")
    ]
    if fixed:
        notes.append(
            ("Fixed by request: " + "; ".join(fixed) + ".", {"data_fixed_context": "true"})
        )
    constants = [
        f"{a['label']} = {node_label(a, a['nodes'][0])}"
        for a in presentation["observed_constants"]
        if a.get("design_role") == "product"
    ]
    if constants:
        notes.append(
            (
                "Constant in recorded preparations (not fixed): " + "; ".join(constants) + ".",
                {"data_observed_context": "true"},
            )
        )
    notes.append(
        (
            f"{presentation['preparations']} exact preparations; "
            f"{len(presentation['traces'])} distinct projected paths. "
            "Exact records remain selectable.",
            {},
        )
    )
    if not fully_enumerated:
        notes.append(
            (
                "Coverage incomplete. Dotted values have no complete witness yet. "
                "Full domains and labels: domains.csv.",
                {},
            )
        )
    if context_count:
        notes.append((f"{context_count} additional query predicates: see query.json.", {}))
    return notes
