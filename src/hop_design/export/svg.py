"""Deterministic dependency-free SVG rendering for typed workflow views."""

from __future__ import annotations

from html import escape

from hop_design.models.views import WorkflowView

_BASE_X = 190
_BASE_WIDTH = 13
_TRACK_HEIGHT = 28
_PANEL_PADDING = 28


def render_workflow_svg(view: WorkflowView) -> bytes:
    """Render only declared view state; no molecular derivation occurs here."""
    panel_heights = tuple(
        _PANEL_PADDING * 2 + max(1, len(panel.tracks)) * _TRACK_HEIGHT + 24 for panel in view.panels
    )
    height = sum(panel_heights) + 20
    width = 960
    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" data-view-kind="{escape(view.kind)}">'
        ),
        "<style>text{font-family:ui-monospace,monospace;font-size:12px}"
        ".title{font-family:system-ui,sans-serif;font-weight:600;font-size:15px}"
        ".panel{fill:#f8fafc;stroke:#94a3b8}.feature{fill:#dbeafe;stroke:#60a5fa}"
        ".pair{stroke:#475569;stroke-width:1.5}</style>",
    ]
    panel_y = 10
    for panel, panel_height in zip(view.panels, panel_heights, strict=True):
        lines.append(
            f'<g data-panel-id="{escape(panel.panel_id)}" transform="translate(10 {panel_y})">'
        )
        lines.append(
            f'<rect class="panel" x="0" y="0" width="940" height="{panel_height}" rx="8"/>'
        )
        lines.append(f'<text class="title" x="16" y="22">{escape(panel.title)}</text>')
        track_y: dict[str, int] = {}
        for index, track in enumerate(panel.tracks):
            y = _PANEL_PADDING + 24 + index * _TRACK_HEIGHT
            track_y[track.track_id] = y
            lines.append(
                f'<g data-track-id="{escape(track.track_id)}" data-strand="{escape(track.strand)}">'
            )
            lines.append(f'<text x="16" y="{y}">{escape(track.label)}</text>')
            lines.append(
                f'<text x="{_BASE_X}" y="{y}" letter-spacing="3">{escape(track.sequence)}</text>'
            )
            lines.append("</g>")
        for feature in panel.features:
            x = _BASE_X + feature.span.start.offset * _BASE_WIDTH
            feature_width = max(2, feature.span.length.value * _BASE_WIDTH)
            y = track_y[feature.track_id] + 5
            lines.append(
                f'<rect class="feature" data-feature-role="{escape(feature.role)}" '
                f'x="{x}" y="{y}" width="{feature_width}" height="5"/>'
            )
        for pairing in panel.pairings:
            x1 = _BASE_X + pairing.left_index * _BASE_WIDTH + 4
            x2 = _BASE_X + pairing.right_index * _BASE_WIDTH + 4
            y1 = track_y[pairing.left_track_id] + 4
            y2 = track_y[pairing.right_track_id] - 10
            if pairing.left_track_id == pairing.right_track_id:
                y2 = y1 + 16
            lines.append(
                f'<line class="pair" data-pair-kind="{escape(pairing.kind)}" '
                f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
            )
        lines.append("</g>")
        panel_y += panel_height
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")


__all__ = ["render_workflow_svg"]
