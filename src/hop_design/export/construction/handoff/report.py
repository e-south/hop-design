"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/handoff/report.py

Explains a selected construction using recorded materials, states, and operations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from html import escape

from hop_design.export.construction.labels import endpoint_label, enzyme_label, state_label
from hop_design.models.construction.complete.pcr.authority import EndpointSequenceFate
from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection

from .materials import external_oligos
from .outcome import product_outcome_lines


def _text(value: str) -> str:
    return "".join(
        f"&#{ord(character)};" if character in "\\`*_[]|#" else escape(character)
        for character in " ".join(value.split())
    )


def _state(state: ConstructionState) -> str:
    lengths = ", ".join(str(len(strand.sequence)) for strand in state.molecules)
    return f"{_text(state_label(state.phase.value))}: strand lengths {lengths} nt"


def render_construction_report(
    projection: CompleteConstructionTrajectoryProjection,
    *,
    selection_reason: str | None,
    enzyme_names: tuple[tuple[str, str], ...] = (),
) -> bytes:
    """Describe the selected route, materials, fragments and endpoint."""
    route = projection.realization
    preparation = route.source_preparation
    program = route.construction_program
    endpoint = route.final_product
    enzymes = sorted(
        {
            operation.enzyme_id
            for reaction in program.reaction_programs
            for stage in reaction.stages
            for operation in stage.operations
        }
    )
    reason = (
        "The caller selected this route."
        if selection_reason is None
        else f"Caller-stated selection reason: {_text(selection_reason)}"
    )
    lines = [
        "# Selected construction",
        "",
        *product_outcome_lines(projection),
        "Changed oligos: compare this selection with an explicit reference; "
        "a single preparation has no change baseline.",
        "",
        f"Payload: `{route.design.payload_sequence}` ({len(route.design.payload_sequence)} nt). "
        "The paired arm is derived; the payload remains unchanged.",
        f"Requested endpoint: {endpoint_label(endpoint.reference.endpoint)}.",
        "",
        reason,
        "",
        "## Required oligonucleotides",
        "",
        f"[oligos.csv](oligos.csv) lists {len(external_oligos(route))} distinct external oligos "
        "with their roles, lengths, and required terminal chemistry. "
        "[oligos.fasta](oligos.fasta) contains those same sequences, "
        "all written 5-prime to 3-prime. "
        "FASTA does not encode modifications; retain the CSV when ordering. "
        "Modeled intermediates are not additional orders.",
        "",
        "Cleavage enzymes used: "
        + ", ".join(_text(enzyme_label(e, enzyme_names)) for e in enzymes)
        + ".",
        "Copying and joining require polymerase and ligase capabilities; "
        "these are not oligo orders.",
        "",
        "## Sequence retained around the payload",
        "",
        f"Source oligo: {len(preparation.source_ssdna.sequence_5prime)} nt. "
        f"Payload interval: [{preparation.payload_source_span.start.offset}, "
        f"{preparation.payload_source_span.end.offset}) in zero-based source coordinates.",
        f"Foldback-local retained sequence: "
        f"{route.foldback_authority.retained_overhead.retained_overhead_nt} nt.",
    ]
    if route.basal_authority is not None:
        lines.append(
            f"Basal-local retained sequence: "
            f"{route.basal_authority.retained_overhead.retained_overhead_nt} nt."
        )
    if endpoint.endpoint_sequence_fate_spans:
        totals: dict[str, int] = {}
        for span in endpoint.endpoint_sequence_fate_spans:
            totals.setdefault(span.endpoint_strand.value, 0)
            if span.fate is not EndpointSequenceFate.PAYLOAD:
                totals[span.endpoint_strand.value] += span.endpoint_span.length.value
        for strand, total in totals.items():
            lines.append(f"Endpoint {strand} strand: {total} non-payload nucleotides.")
    else:
        non_payload_nt = len(endpoint.reference.sequence) - 2 * len(route.design.payload_sequence)
        lines.append(f"Endpoint strand: {non_payload_nt} non-payload nucleotides.")
    endpoint_lengths = ", ".join(str(len(strand.sequence)) for strand in endpoint.strands)
    lines.extend(
        [
            "Local retained sequence and whole-endpoint non-payload sequence are different "
            "quantities; source handles are not automatically retained in the endpoint.",
            "",
            "## Expected molecular steps",
            "",
            f"1. Source copying with the two source primers → {_state(preparation.product_state)}.",
        ]
    )
    reactions = {item.program_id: item for item in program.reaction_programs}
    states = {item.state_id: item for item in program.states}
    for index, transition in enumerate(program.transitions, start=2):
        operation = transition.kind.value.replace("_", " ")
        if transition.reaction_program_id is not None:
            reaction = reactions[transition.reaction_program_id]
            stages = [
                " + ".join(
                    dict.fromkeys(
                        _text(enzyme_label(item.enzyme_id, enzyme_names))
                        for item in stage.operations
                    )
                )
                for stage in reaction.stages
            ]
            operation += f" ({'; then '.join(stages)})"
        lines.append(f"{index}. {operation} → {_state(states[transition.post_state_id])}.")
    lines.extend(["", "## Fragment selection", ""])
    certificate = projection.source_partition_certificate
    if certificate is None:
        lines.append(
            "Unwanted-fragment removal is not verified by a bound source-partition result. "
            "The stated strand selection remains a preparation condition to resolve."
        )
    else:
        for disposition, label in (("required", "Retained"), ("sacrificial", "Unwanted")):
            lengths = ", ".join(
                str(fragment.length_nt)
                for fragment in certificate.fragments
                if fragment.disposition.value == disposition
            )
            lines.append(f"{label} separated fragment lengths: {lengths} nt.")
    lines.extend(
        [
            "",
            "## Expected endpoint",
            "",
            f"Topology: {endpoint.reference.topology.replace('_', ' ')}. "
            f"Strand lengths: {endpoint_lengths} nt.",
        ]
    )
    for end in endpoint.cohesive_ends:
        lines.append(
            f"{end.product_end.capitalize()} cohesive end: `{end.sequence}` (5-prime to 3-prime), "
            f"{end.overhang_end.value.replace('_', ' ')} overhang on "
            f"{_text(end.protruding_strand_id)}."
        )
    if endpoint.cohesive_ends:
        lines.append(
            "Compare both oriented ends and "
            "terminal chemistry with the intended receiving DNA before assembly."
        )
    lines.extend(
        [
            "",
            "## Exact details",
            "",
            "[Molecular record](projection.json) · [State diagram](projection.svg). "
            "These preserve the exact bindings, coordinates, bonds, and sequences.",
            "",
            f"Result: `{projection.source_result_id}`.",
            f"Realization: `{route.materialized_realization_id}`.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")
