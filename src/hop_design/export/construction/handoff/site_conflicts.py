"""Plain molecular locations from replayed actionable-site diagnostics."""

from typing import Any


def site_conflict_lines(sites: list[dict[str, Any]]) -> list[str]:
    return [
        f"{s['enzyme_name']} ({s['enzyme_id']}): {s['recognition_sequence']} "
        "at reference positions "
        f"[{s['recognition_start']}, {s['recognition_end']}) of {s['molecule_id']}; "
        f"{s['processing_phase']} stage {s['stage_id']}, state {s['state_id']}; "
        f"orientation {s['orientation']}; cuts {s['reference_cut']}/{s['complement_cut']}. "
        "Positions and cut boundaries are zero-based; intervals exclude their final boundary."
        for s in sites
    ]
