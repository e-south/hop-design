"""Deterministic dependency-free SVG rendering for typed workflow views."""

from __future__ import annotations

from html import escape

from hop_design.models.views import TrackDirection, ViewTrack, WorkflowView

_MIN_BASE_X = 210
_BASE_WIDTH = 13
_TRACK_HEIGHT = 40
_PANEL_PADDING = 28
_TRANSITION_GAP = 28


def _display_sequence(track: ViewTrack) -> str:
    if track.direction is TrackDirection.REVERSE:
        return track.sequence[::-1]
    return track.sequence


def _display_index(track: ViewTrack, index: int) -> int:
    if track.direction is TrackDirection.REVERSE:
        return len(track.sequence) - index - 1
    return index


def _display_span(track: ViewTrack, start: int, end: int) -> tuple[int, int]:
    if track.direction is TrackDirection.REVERSE:
        return len(track.sequence) - end, len(track.sequence) - start
    return start, end


def _termini(track: ViewTrack) -> tuple[str, str]:
    if track.direction is TrackDirection.REVERSE:
        return "3\u2032", "5\u2032"
    return "5\u2032", "3\u2032"


def render_workflow_svg(view: WorkflowView) -> bytes:
    """Render only declared view state; no molecular derivation occurs here."""
    longest_track = max(len(track.sequence) for panel in view.panels for track in panel.tracks)
    longest_label = max(len(track.label) for panel in view.panels for track in panel.tracks)
    sequence_x = max(_MIN_BASE_X, 28 + longest_label * 8)
    panel_heights = tuple(
        _PANEL_PADDING * 2 + max(1, len(panel.tracks)) * _TRACK_HEIGHT + 24 for panel in view.panels
    )
    transition_height = max(0, len(view.panels) - 1) * _TRANSITION_GAP
    height = sum(panel_heights) + transition_height + 20
    width = max(960, sequence_x + longest_track * _BASE_WIDTH + 70)
    panel_width = width - 20
    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" data-view-kind="{escape(view.kind)}" '
            'role="img">'
        ),
        f"<title>{escape(view.kind.replace('_', ' '))}</title>",
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
        'refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" '
        'fill="#64748b"/></marker></defs>',
        "<style>text{font-family:ui-monospace,monospace;font-size:12px}"
        ".title{font-family:system-ui,sans-serif;font-weight:600;font-size:15px}"
        ".panel{fill:#f8fafc;stroke:#94a3b8}.feature{fill:#dbeafe;stroke:#60a5fa}"
        ".feature-label{font-family:system-ui,sans-serif;font-size:10px;fill:#1e3a8a}"
        ".terminus{fill:#64748b}.pair{stroke-width:1.8}"
        ".pair-watson_crick{stroke:#475569}"
        ".pair-gt_wobble{stroke:#d97706;stroke-dasharray:3 2}"
        ".pair-hard_mismatch{stroke:#dc2626;stroke-dasharray:2 2}"
        ".transition{stroke:#64748b;stroke-width:1.5;marker-end:url(#arrow)}</style>",
    ]
    panel_y = 10
    previous_panel: tuple[str, int] | None = None
    for panel, panel_height in zip(view.panels, panel_heights, strict=True):
        if previous_panel is not None:
            previous_id, previous_bottom = previous_panel
            arrow_x = panel_width / 2
            lines.append(
                f'<line class="transition" data-transition-from="{escape(previous_id)}" '
                f'data-transition-to="{escape(panel.panel_id)}" x1="{arrow_x}" '
                f'y1="{previous_bottom + 5}" x2="{arrow_x}" y2="{panel_y - 7}"/>'
            )
        lines.append(
            f'<g data-panel-id="{escape(panel.panel_id)}" transform="translate(10 {panel_y})">'
        )
        lines.append(
            f'<rect class="panel" x="0" y="0" width="{panel_width}" '
            f'height="{panel_height}" rx="8"/>'
        )
        lines.append(f'<text class="title" x="16" y="22">{escape(panel.title)}</text>')
        tracks = {track.track_id: track for track in panel.tracks}
        track_y: dict[str, int] = {}
        for index, track in enumerate(panel.tracks):
            y = _PANEL_PADDING + 24 + index * _TRACK_HEIGHT
            track_y[track.track_id] = y
            left_terminus, right_terminus = _termini(track)
            displayed = _display_sequence(track)
            sequence_end = sequence_x + len(displayed) * _BASE_WIDTH
            lines.append(
                f'<g data-track-id="{escape(track.track_id)}" data-strand="{escape(track.strand)}" '
                f'data-direction="{escape(track.direction)}">'
            )
            lines.append(f'<text x="16" y="{y}">{escape(track.label)}</text>')
            lines.append(
                f'<text class="terminus" x="{sequence_x - 25}" y="{y}">{left_terminus}</text>'
            )
            lines.append(
                f'<text x="{sequence_x}" y="{y}" letter-spacing="3">{escape(displayed)}</text>'
            )
            lines.append(
                f'<text class="terminus" x="{sequence_end + 2}" y="{y}">{right_terminus}</text>'
            )
            lines.append("</g>")
        for feature_index, feature in enumerate(panel.features):
            track = tracks[feature.track_id]
            start, end = _display_span(
                track,
                feature.span.start.offset,
                feature.span.end.offset,
            )
            x = sequence_x + start * _BASE_WIDTH
            feature_width = max(2, (end - start) * _BASE_WIDTH)
            y = track_y[feature.track_id] + 7
            lines.append(
                f'<rect class="feature" data-feature-role="{escape(feature.role)}" '
                f'x="{x}" y="{y}" width="{feature_width}" height="5"/>'
            )
            lines.append(
                f'<text class="feature-label" x="{x}" '
                f'y="{y + 16 + (feature_index % 3) * 12}">{escape(feature.label)}</text>'
            )
        for pairing in panel.pairings:
            left_track = tracks[pairing.left_track_id]
            right_track = tracks[pairing.right_track_id]
            left_index = _display_index(left_track, pairing.left_index)
            right_index = _display_index(right_track, pairing.right_index)
            x1 = sequence_x + left_index * _BASE_WIDTH + 4
            x2 = sequence_x + right_index * _BASE_WIDTH + 4
            y1 = track_y[pairing.left_track_id] + 4
            y2 = track_y[pairing.right_track_id] - 10
            attributes = (
                f'class="pair pair-{escape(pairing.kind)}" '
                f'data-pair-kind="{escape(pairing.kind)}" data-display-aligned="true"'
            )
            if pairing.left_track_id == pairing.right_track_id:
                anchor_y = track_y[pairing.left_track_id] - 7
                control_y = max(25, anchor_y - abs(x2 - x1) / 5)
                lines.append(
                    f'<path {attributes} fill="none" '
                    f'd="M{x1},{anchor_y} Q{(x1 + x2) / 2},{control_y} {x2},{anchor_y}"/>'
                )
            else:
                lines.append(f'<line {attributes} x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
        lines.append("</g>")
        previous_panel = (panel.panel_id, panel_y + panel_height)
        panel_y += panel_height + _TRANSITION_GAP
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")


__all__ = ["render_workflow_svg"]
