"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/handoff/comparison.py

Compares recorded molecular properties of two explicitly selected constructions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete import MaterializedConstructionRealization
from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.complete.state import ConstructionStatePhase
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection

from .materials import external_oligos
from .report import _text

_MATERIAL_LABELS = {
    MaterialUseRole.SOURCE_SSDNA: "Source oligo",
    MaterialUseRole.SOURCE_MATERIALIZATION_FORWARD_PRIMER: "Source forward primer",
    MaterialUseRole.SOURCE_MATERIALIZATION_REVERSE_PRIMER: "Source reverse primer",
    MaterialUseRole.LIGATION_ADAPTER: "Adapter",
    MaterialUseRole.ENDPOINT_FORWARD_PRIMER: "Endpoint forward primer",
    MaterialUseRole.ENDPOINT_REVERSE_PRIMER: "Endpoint reverse primer",
}


def _sequence(sequence: str, five_prime: str, three_prime: str) -> str:
    return f"{sequence} ({len(sequence)} nt; 5-prime {five_prime}; 3-prime {three_prime})"


def _operation_order(route: MaterializedConstructionRealization) -> str:
    program = route.construction_program
    reactions = {item.program_id: item for item in program.reaction_programs}
    steps = ["source copying"]
    for transition in program.transitions:
        step = transition.kind.value.replace("_", " ")
        if transition.reaction_program_id is not None:
            stages = reactions[transition.reaction_program_id].stages
            step += (
                " ("
                + "; then ".join(
                    " + ".join(sorted({operation.enzyme_id for operation in stage.operations}))
                    for stage in stages
                )
                + ")"
            )
        steps.append(step)
    return " → ".join(steps)


def _facts(projection: CompleteConstructionTrajectoryProjection) -> dict[str, str]:
    route = projection.realization
    endpoint = route.final_product
    payload_span = route.source_preparation.payload_source_span
    facts = {
        "Payload": route.design.payload_sequence,
        "Requested endpoint": endpoint.reference.endpoint.value.replace("_", " "),
        "Endpoint topology": endpoint.reference.topology.replace("_", " "),
        "Payload source interval": f"[{payload_span.start.offset}, {payload_span.end.offset})",
        "Closing-flank retained sequence (nt)": str(
            route.foldback_authority.retained_overhead.retained_overhead_nt
        ),
        "Attachment-flank retained sequence (nt)": (
            "not required"
            if route.basal_authority is None
            else str(route.basal_authority.retained_overhead.retained_overhead_nt)
        ),
        "Hairpin-encoding sequence": route.design.encoding_sequence,
    }
    resolutions = []
    for material, uses in external_oligos(route):
        for use in uses:
            label = _MATERIAL_LABELS[use.role]
            facts[label] = _sequence(
                material.sequence_5prime,
                material.five_prime_end.value,
                material.three_prime_end.value,
            )
            resolutions.append(f"{label}: {use.specification_resolution_mode.value}")
    facts["Material specification choices"] = "; ".join(resolutions)
    facts["Operation/enzyme order"] = _operation_order(route)
    certificate = projection.source_partition_certificate
    if certificate is None:
        facts["Fragment removal"] = "unresolved: no bound removal program"
    else:
        facts["Fragment removal"] = "; ".join(
            f"{fragment.precursor_strand.value} "
            f"[{fragment.source_span.start.offset}, {fragment.source_span.end.offset}) "
            f"{fragment.length_nt} nt {fragment.disposition.value}"
            for fragment in certificate.fragments
        )
        facts["Removal-rule allowance (nt)"] = str(
            certificate.selected_maximum_sacrificial_fragment_nt
        )
    for state in route.construction_program.states:
        if state.phase is ConstructionStatePhase.HAIRPIN_PCR_DUPLEX:
            facts["PCR strand lengths (nt)"] = ", ".join(
                str(len(strand.sequence)) for strand in state.molecules
            )
    for index, strand in enumerate(endpoint.strands, start=1):
        facts[f"Endpoint strand {index}"] = _sequence(
            strand.sequence, strand.five_prime_end.value, strand.three_prime_end.value
        )
    ends = {end.product_end: end for end in endpoint.cohesive_ends}
    for side in ("left", "right"):
        end = ends.get(side)
        facts[f"{side.capitalize()} cohesive end"] = (
            "not generated"
            if end is None
            else f"{end.sequence} (5-prime to 3-prime; "
            f"{end.overhang_end.value.replace('_', ' ')} overhang)"
        )
    return facts


def render_construction_comparison(
    left: CompleteConstructionTrajectoryProjection,
    right: CompleteConstructionTrajectoryProjection,
    *,
    left_status: str,
    right_status: str,
) -> str:
    """Render a property comparison, not a new route or molecular equivalence claim."""
    left_facts, right_facts = _facts(left), _facts(right)
    lines = [
        "# Compare selected constructions",
        "",
        "Sequences are written 5-prime to 3-prime; intervals are zero-based and half-open. "
        "Same/changed compares each displayed property, not route identity or performance.",
        f"Composition coverage: left {left_status}; right {right_status}.",
        "Both selected routes resolved in their respective models; "
        "this does not make a truncated search exhaustive and "
        "does not describe upstream scaffold-generation coverage.",
        "",
        "| Property | Comparison | Left | Right |",
        "| --- | --- | --- | --- |",
    ]
    for label in dict.fromkeys((*left_facts, *right_facts)):
        first, second = (
            left_facts.get(label, "not required"),
            right_facts.get(label, "not required"),
        )
        comparison = "same" if first == second else "changed"
        lines.append(f"| {label} | {comparison} | {_text(first)} | {_text(second)} |")
    lines.extend(
        [
            "",
            "This is not a ranking. Operation order does not compare every binding or cut; "
            "inspect each route for exact coordinates, pairing, bonds, and lineage. "
            "Matching sequence and chemistry do not establish equal experimental performance. "
            "Fragment removal is a model rule, not a prediction of cleanup recovery.",
            "",
            f"Left result: `{left.source_result_id}`.",
            f"Left realization: `{left.realization.materialized_realization_id}`.",
            f"Right result: `{right.source_result_id}`.",
            f"Right realization: `{right.realization.materialized_realization_id}`.",
        ]
    )
    return "\n".join(lines) + "\n"
