"""Align hairpin observations by molecular region, independently of absolute offsets."""

from pydantic import JsonValue

from hop_design.models.construction.hairpin_geometry import HairpinArchitecture, describe_hairpin
from hop_design.models.construction.projections.trajectory import (
    CompleteConstructionTrajectoryProjection,
)


def regional_facts(trajectory: CompleteConstructionTrajectoryProjection) -> dict[str, JsonValue]:
    try:
        architecture = describe_hairpin(trajectory.realization)
    except ValueError as error:
        # The comparison also serves valid routes outside the portrait's narrower
        # topology/lineage domain. Preserve their preparation comparison and expose
        # the missing regional view explicitly; never manufacture an architecture.
        return {"hairpin.availability": "unsupported", "hairpin.unavailable_reason": str(error)}
    return architecture_facts(architecture)


def architecture_facts(architecture: HairpinArchitecture) -> dict[str, JsonValue]:
    """Describe one verified architecture in region-local rather than absolute coordinates."""
    strand = architecture.state.molecules[0]
    regions = region_spans(architecture)
    facts: dict[str, JsonValue] = {
        "hairpin.availability": "available",
        "hairpin.stage": architecture.state.phase.value,
        "hairpin.stage_role": architecture.stage_role,
        "hairpin.stem_bp": architecture.stem_bp,
        "hairpin.loop_nt": architecture.loop_nt,
        "hairpin.loop_side_paired_bp": architecture.loop_side_paired_bp,
        "hairpin.open_side_paired_positions": architecture.open_side_paired_positions,
        "hairpin.five_prime_unpaired_nt": architecture.five_prime_unpaired_nt,
        "hairpin.three_prime_unpaired_nt": architecture.three_prime_unpaired_nt,
        "hairpin.five_prime_end": strand.five_prime_end.value,
        "hairpin.three_prime_end": strand.three_prime_end.value,
    }
    pairs = architecture.ordered_contacts
    for region, (start, end) in regions.items():
        key = f"hairpin.region.{region}"
        facts[key + ".sequence"] = strand.sequence[start:end]
        facts[key + ".span"] = [start, end]
        # Contacts are aligned within each named region, not by absolute offsets.
        if region.endswith("primary"):
            facts[key + ".contacts"] = [
                {
                    "offset": p.left_index - start,
                    "left_base": p.left_base,
                    "right_base": p.right_base,
                    "kind": p.kind.value,
                }
                for p in pairs
                if start <= p.left_index < end
            ]
        facts[key + ".joins"] = [
            boundary - start for boundary in architecture.join_boundaries if start < boundary <= end
        ]
    return facts


def region_spans(architecture: HairpinArchitecture) -> dict[str, tuple[int, int]]:
    """Partition the verified hairpin into disjoint, orientation-specific regions."""
    strand = architecture.state.molecules[0]
    primary, returned = architecture.stem_primary_span, architecture.stem_return_span
    outer, inner = architecture.paired_primary_span, architecture.paired_return_span
    loop = architecture.loop_span
    return {
        "terminal_primary": (0, outer.start.offset),
        "open_primary": (outer.start.offset, primary.start.offset),
        "stem_primary": (primary.start.offset, primary.end.offset),
        "closing_primary": (primary.end.offset, loop.start.offset),
        "loop": (loop.start.offset, loop.end.offset),
        "closing_return": (loop.end.offset, returned.start.offset),
        "stem_return": (returned.start.offset, returned.end.offset),
        "open_return": (returned.end.offset, inner.end.offset),
        "terminal_return": (inner.end.offset, len(strand.sequence)),
    }
