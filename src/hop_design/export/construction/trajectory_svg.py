"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/trajectory_svg.py

Renders one exact selected construction chronology as a restrained SVG.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete import ConstructionState
from hop_design.models.construction.projections import (
    CompleteConstructionTrajectoryProjection,
)
from hop_design.models.coordinates import Boundary
from hop_design.models.molecular_state import StrandPairObservation
from hop_design.models.reactions import ReactionProgram

from .svg_common import escape, render_document, short_id

_PAIR_CHUNK_SIZE = 4
_SEQUENCE_CHUNK_SIZE = 48


def _strand_aliases(states: tuple[ConstructionState, ...]) -> dict[str, str]:
    aliases: dict[str, str] = {}

    def register(strand_id: str) -> None:
        if strand_id not in aliases:
            aliases[strand_id] = f"S{len(aliases) + 1}"

    for state in states:
        for strand in state.molecules:
            register(strand.strand_id)
        for pair in state.pairings:
            register(pair.left_strand_id)
            register(pair.right_strand_id)
        for item in state.formed_bonds:
            register(item.bond.upstream_strand_id)
            register(item.bond.downstream_strand_id)
            register(item.product_strand_id)
    return aliases


def _cut_offset(boundary: Boundary | None) -> str:
    return "none" if boundary is None else str(boundary.offset)


def _state_association_metadata(state: ConstructionState) -> str:
    pairings = "".join(
        f'<g data-pair-left-strand="{escape(pair.left_strand_id)}" '
        f'data-pair-left-index="{pair.left_index}" '
        f'data-pair-left-base="{escape(pair.left_base)}" '
        f'data-pair-right-strand="{escape(pair.right_strand_id)}" '
        f'data-pair-right-index="{pair.right_index}" '
        f'data-pair-right-base="{escape(pair.right_base)}" '
        f'data-pair-kind="{escape(pair.kind.value)}"/>'
        for pair in state.pairings
    )
    bonds = "".join(
        f'<g data-bond-upstream-strand="{escape(item.bond.upstream_strand_id)}" '
        f'data-bond-upstream-end="{escape(item.bond.upstream_end.value)}" '
        f'data-bond-downstream-strand="{escape(item.bond.downstream_strand_id)}" '
        f'data-bond-downstream-end="{escape(item.bond.downstream_end.value)}" '
        f'data-bond-product-strand="{escape(item.product_strand_id)}"/>'
        for item in state.formed_bonds
    )
    return pairings + bonds


def _visible_association_rows(
    state: ConstructionState,
    *,
    aliases: dict[str, str],
    y_start: int,
) -> tuple[str, int]:
    grouped_pairs: dict[tuple[str, str, str], list[StrandPairObservation]] = {}
    for pair in state.pairings:
        grouped_pairs.setdefault(
            (pair.left_strand_id, pair.right_strand_id, pair.kind.value),
            [],
        ).append(pair)

    rows: list[str] = []
    row_index = 0
    for (left_strand_id, right_strand_id, pair_kind), pairs in grouped_pairs.items():
        for start in range(0, len(pairs), _PAIR_CHUNK_SIZE):
            chunk = pairs[start : start + _PAIR_CHUNK_SIZE]
            left_relation = ",".join(f"{pair.left_index}:{pair.left_base}" for pair in chunk)
            right_relation = ",".join(f"{pair.right_index}:{pair.right_base}" for pair in chunk)
            rows.append(
                f'<text x="390" y="{y_start + row_index * 18}" class="small" '
                f'style="font-family:monospace" data-layout-row="bounded" '
                f'data-visible-association="pairing" '
                f'data-left-strand-id="{escape(left_strand_id)}" '
                f'data-right-strand-id="{escape(right_strand_id)}" '
                f'data-pair-kind="{escape(pair_kind)}" '
                f'data-left-relations="{escape(left_relation)}" '
                f'data-right-relations="{escape(right_relation)}">'
                f"{escape(aliases[left_strand_id])} [{escape(left_relation)}] ↔ "
                f"{escape(aliases[right_strand_id])} [{escape(right_relation)}] · "
                f"{escape(pair_kind)}</text>"
            )
            row_index += 1
    for item in state.formed_bonds:
        bond = item.bond
        rows.append(
            f'<text x="390" y="{y_start + row_index * 18}" class="small" '
            f'style="font-family:monospace" data-layout-row="bounded" '
            f'data-visible-association="bond" '
            f'data-upstream-strand-id="{escape(bond.upstream_strand_id)}" '
            f'data-downstream-strand-id="{escape(bond.downstream_strand_id)}" '
            f'data-product-strand-id="{escape(item.product_strand_id)}">'
            f"{escape(aliases[bond.upstream_strand_id])} 3-prime → "
            f"{escape(aliases[bond.downstream_strand_id])} 5-prime → "
            f"{escape(aliases[item.product_strand_id])}</text>"
        )
        row_index += 1
    return "".join(rows), row_index


def _visible_strand_rows(
    state: ConstructionState,
    *,
    aliases: dict[str, str],
    y_start: int,
) -> tuple[str, int]:
    rows: list[str] = []
    row_index = 0
    for strand in state.molecules:
        alias = aliases[strand.strand_id]
        rows.append(
            f'<g data-strand-id="{escape(strand.strand_id)}" '
            f'data-sequence="{escape(strand.sequence)}" '
            f'data-five-prime-end="{escape(strand.five_prime_end.value)}" '
            f'data-three-prime-end="{escape(strand.three_prime_end.value)}">'
            f'<text x="390" y="{y_start + row_index * 18}" class="small" '
            f'style="font-family:monospace" data-layout-row="bounded" '
            f'data-visible-strand-label="{escape(strand.strand_id)}">'
            f"{escape(alias)} · strand {escape(short_id(strand.strand_id))} · ends "
            f"{escape(strand.five_prime_end.value)}/{escape(strand.three_prime_end.value)}"
            f"</text>"
        )
        row_index += 1
        sequence_chunks = tuple(
            strand.sequence[start : start + _SEQUENCE_CHUNK_SIZE]
            for start in range(0, len(strand.sequence), _SEQUENCE_CHUNK_SIZE)
        )
        for chunk_index, chunk in enumerate(sequence_chunks):
            boundary_prefix = "5-prime " if chunk_index == 0 else ""
            boundary_suffix = " 3-prime" if chunk_index == len(sequence_chunks) - 1 else ""
            rows.append(
                f'<text x="414" y="{y_start + row_index * 18}" class="small" '
                f'style="font-family:monospace" data-layout-row="bounded" '
                f'data-visible-strand-id="{escape(strand.strand_id)}" '
                f'data-sequence-chunk-index="{chunk_index}" '
                f'data-sequence-chunk="{escape(chunk)}">'
                f"{escape(alias)} · {boundary_prefix}{escape(chunk)}{boundary_suffix}</text>"
            )
            row_index += 1
        rows.append("</g>")
    return "".join(rows), row_index


def _reaction_metadata(program: ReactionProgram) -> tuple[str, str]:
    annotations: list[str] = []
    metadata: list[str] = []
    for stage in program.stages:
        for operation in stage.operations:
            binding = operation.intended_binding
            reference_cut = _cut_offset(binding.reference_cut)
            complement_cut = _cut_offset(binding.complement_cut)
            annotations.append(
                f"{operation.operation_id}: span "
                f"{binding.recognition_span.start.offset}-{binding.recognition_span.end.offset}; "
                f"cuts {reference_cut}/{complement_cut}"
            )
            metadata.append(
                f'<g data-stage-id="{escape(stage.stage_id)}" '
                f'data-operation-id="{escape(operation.operation_id)}" '
                f'data-enzyme-id="{escape(operation.enzyme_id)}" '
                f'data-molecule-id="{escape(operation.molecule_id)}" '
                f'data-enzyme-role="{escape(operation.role.value)}" '
                f'data-recognition-start="{binding.recognition_span.start.offset}" '
                f'data-recognition-end="{binding.recognition_span.end.offset}" '
                f'data-recognition-orientation="{escape(binding.orientation.value)}" '
                f'data-reference-cut="{reference_cut}" '
                f'data-complement-cut="{complement_cut}"/>'
            )
    return "; ".join(annotations), "".join(metadata)


def render_complete_trajectory_svg(
    projection: CompleteConstructionTrajectoryProjection,
) -> bytes:
    """Render recorded construction states and transitions without inferring evidence."""
    realization = projection.realization
    program = realization.construction_program
    claims = realization.claim_boundary
    rows: list[str] = []
    cursor = 190
    reaction_programs = {item.program_id: item for item in program.reaction_programs}
    aliases = _strand_aliases(program.states)
    for index, state in enumerate(program.states):
        y = cursor
        phase = state.phase.value.replace("_", " ")
        strand_ids = " ".join(item.strand_id for item in state.molecules)
        strand_rows, strand_row_count = _visible_strand_rows(
            state,
            aliases=aliases,
            y_start=y + 22,
        )
        association_rows, association_row_count = _visible_association_rows(
            state,
            aliases=aliases,
            y_start=y + 22 + strand_row_count * 18,
        )
        rows.append(
            f'<g data-state-id="{escape(state.state_id)}" '
            f'data-phase="{escape(state.phase.value)}" '
            f'data-strand-ids="{escape(strand_ids)}">'
            f'<circle cx="92" cy="{y}" r="8" class="state-node"/>'
            f'<text x="122" y="{y + 6}" class="body">{escape(phase)}</text>'
            f'<text x="390" y="{y + 4}" class="small">'
            f"{len(state.molecules)} exact strand(s) · {len(state.pairings)} pair(s) · "
            f"{len(state.formed_bonds)} bond(s)</text>"
            f"{strand_rows}{association_rows}{_state_association_metadata(state)}</g>"
        )
        state_height = max(
            74,
            52 + (strand_row_count + association_row_count) * 18,
        )
        if index < len(program.transitions):
            transition = program.transitions[index]
            label = transition.kind.value.replace("_", " ")
            reaction_text = ""
            reaction_metadata = ""
            if transition.reaction_program_id is not None:
                reaction_text, reaction_metadata = _reaction_metadata(
                    reaction_programs[transition.reaction_program_id]
                )
            rows.append(
                f'<g data-transition-id="{escape(transition.transition_id)}" '
                f'data-transition-kind="{escape(transition.kind.value)}">'
                f'<line x1="92" y1="{y + 10}" x2="92" '
                f'y2="{y + state_height + 16}" class="rule"/>'
                f'<text x="122" y="{y + state_height}" class="small">{escape(label)}</text>'
                f'<text x="390" y="{y + state_height}" class="small">'
                f"{escape(reaction_text)}</text>{reaction_metadata}</g>"
            )
        cursor += state_height + 30
    cohesive_rows = "".join(
        f'<g data-cohesive-product-end="{escape(end.product_end)}" '
        f'data-cohesive-sequence="{escape(end.sequence)}" '
        f'data-cohesive-protruding-strand="{escape(end.protruding_strand_id)}" '
        f'data-cohesive-overhang-end="{escape(end.overhang_end.value)}" '
        f'data-cohesive-source-start="{end.source_span.start.offset}" '
        f'data-cohesive-source-end="{end.source_span.end.offset}" '
        f'data-cohesive-primary-cut="{end.primary_cut.offset}" '
        f'data-cohesive-complementary-cut="{end.complementary_cut.offset}">'
        f'<text x="122" y="{cursor + 20 + end_index * 22}" class="small" '
        f'style="font-family:monospace" data-layout-row="bounded">'
        f"{escape(end.product_end)} cohesive end · {escape(end.sequence)} · "
        f"{escape(aliases[end.protruding_strand_id])} · "
        f"{escape(end.overhang_end.value)}</text></g>"
        for end_index, end in enumerate(realization.final_product.cohesive_ends)
    )
    if cohesive_rows:
        rows.append(
            f'<text x="72" y="{cursor}" class="label">Recorded clone cohesive ends</text>'
            f"{cohesive_rows}"
        )
        cursor += 50 + len(realization.final_product.cohesive_ends) * 22
    title = f"The selected digital route records {len(program.states)} exact molecular states."
    boundary = "No physical construction, QC, or biological activity is established."
    body = f"""
<g data-projection-id="{escape(projection.projection_id)}"
data-projection-schema="{escape(projection.schema_id)}"
data-renderer-version="{escape(projection.renderer_version)}"
data-result-id="{escape(projection.source_result_id)}"
data-realization-id="{escape(realization.materialized_realization_id)}"
data-composition-ordinal="{projection.composition_ordinal}"
data-endpoint="{escape(realization.final_product.reference.endpoint.value)}"
data-digital-design="{escape(claims.digital_design.value)}"
data-method="{escape(claims.method.value)}"
data-physical-construction="{escape(claims.physical_construction.value)}"
data-quality-control="{escape(claims.quality_control.value)}"
data-biological-activity="{escape(claims.biological_activity.value)}">
<text x="72" y="58" class="title">{escape(title)}</text>
<text x="72" y="96" class="subtitle">Digital route only · selected composition ordinal
{projection.composition_ordinal}</text>
<text x="72" y="128" class="small">{escape(boundary)}</text>
</g>
<line x1="72" y1="150" x2="1128" y2="150" class="rule"/>
{"".join(rows)}
"""
    return render_document(
        title=title,
        body=body,
        height=max(360, cursor + 30),
        description="Exact selected digital construction chronology from verified route state.",
    )


__all__ = ["render_complete_trajectory_svg"]
