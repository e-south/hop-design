"""Project recorded preparation facts for structured and human comparisons."""

from hop_design.export.construction.labels import endpoint_label
from hop_design.models.construction.complete import MaterializedConstructionRealization
from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.complete.state import ConstructionStatePhase
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection
from hop_design.models.construction.projections.materials import external_oligos

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
        "Requested endpoint": endpoint_label(endpoint.reference.endpoint),
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
