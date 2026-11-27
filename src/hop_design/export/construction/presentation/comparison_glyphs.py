"""
--------------------------------------------------------------------------------
HOP Design
hop-design/src/hop_design/export/construction/presentation/comparison_glyphs.py

Share fixed field-type schematics between browser and static comparison displays.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from collections.abc import Iterable
from typing import Any

INK, PALE = "#233c43", "#dce6e1"
_ORDER = (
    "shape.open_side_paired_positions",
    "shape.loop_side_paired_bp",
    "shape.loop_nt",
    "shape.left_gap",
    "shape.right_gap",
    "sequences.basal_pairs",
    "sequences.foldback_pairs",
    "sequences.loop",
    "interfaces.left_word",
    "interfaces.right_word",
    "processing.basal_method",
    "processing.foldback_method",
    "processing.release_method",
)


def _node(tag: str, **attrs: Any) -> dict[str, Any]:
    return {
        "tag": tag,
        "attrs": {key.replace("_", "-"): str(value) for key, value in attrs.items()},
    }


def _line(
    x1: float, y1: float, x2: float, y2: float, *, linecap: str = "round", **attrs: Any
) -> dict[str, Any]:
    return _node(
        "line",
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        stroke=INK,
        stroke_width=0.6,
        stroke_linecap=linecap,
        **attrs,
    )


def _paired(left: float, right: float, contacts: Iterable[float]) -> list[dict[str, Any]]:
    return [
        *[_line(x, -1.6, x, 1.6) for x in contacts],
        _node(
            "line",
            x1=left,
            y1=-1.6,
            x2=right,
            y2=-1.6,
            stroke=INK,
            stroke_width=0.85,
            stroke_linecap="butt",
            data_measured_flank="true",
        ),
        _node(
            "line",
            x1=left,
            y1=1.6,
            x2=right,
            y2=1.6,
            stroke=INK,
            stroke_width=0.85,
            stroke_linecap="butt",
            data_measured_flank="true",
        ),
    ]


def _fixed(left: float, right: float) -> dict[str, Any]:
    middle = (left + right) / 2
    return {
        "tag": "g",
        "attrs": {"data-fixed-stem": "omitted sequence; pale paired context"},
        "children": [
            _line(left, y, right, y, linecap="butt", stroke_opacity=0.28) for y in (-1.6, 1.6)
        ]
        + [
            _node("circle", cx=x, cy=0, r=0.16, fill=INK, fill_opacity=0.45)
            for x in (middle - 0.9, middle, middle + 0.9)
        ],
    }


def _loop() -> list[dict[str, Any]]:
    return [
        _node(
            "path",
            d="M-3,2.2 V0.4 A3,3 0 0 1 3,0.4 V2.2",
            fill="none",
            stroke=INK,
            stroke_width=0.85,
            stroke_linejoin="round",
            stroke_linecap="round",
        )
    ]


def _end(right: bool) -> list[dict[str, Any]]:
    sign = -1 if right else 1
    return [
        _node(
            "path",
            d="M-4,-2.35 H1 V-0.8 H-4" if right else "M4,-2.35 H-4 V-0.8 H4",
            fill=PALE,
            stroke=INK,
            stroke_width=0.7,
            stroke_linejoin="round",
            stroke_linecap="round",
        ),
        _node(
            "path",
            d="M-4,0.8 H4 V2.35 H-4" if right else "M4,0.8 H-1 V2.35 H4",
            fill=PALE,
            stroke=INK,
            stroke_width=0.7,
            stroke_linejoin="round",
            stroke_linecap="round",
        ),
        *[_line(x * sign, -0.8, x * sign, 0.8) for x in (0, 1.5, 3)],
    ]


def _enzyme(release: bool) -> list[dict[str, Any]]:
    parts: list[tuple[float, float, float]] = [(-4, -2.25, 2.4), (0, -2.25, 4)]
    parts += [(-4, 0.95, 4), (1.6, 0.95, 2.4)] if release else [(-4, 0.95, 8)]
    return [
        _node(
            "rect", x=x, y=y, width=w, height=1.3, rx=0.35, fill=PALE, stroke=INK, stroke_width=0.7
        )
        for x, y, w in parts
    ]


def _glyph(key: str) -> dict[str, Any]:
    field = key.split(".")[-1]
    if field == "open_side_paired_positions":
        nodes = [*_paired(-4.675, -2.475, (-3.575,)), _fixed(-2.475, 4.675)]
    elif field == "loop_side_paired_bp":
        nodes = [
            _node(
                "path",
                d="M2.725,-1.6 A1.6,1.6 0 0 1 2.725,1.6",
                fill="none",
                stroke=INK,
                stroke_width=0.6,
                stroke_opacity=0.28,
            )
        ]
        nodes += [*_paired(0.8, 2.725, (1.7625,)), _fixed(-4.625, 0.8)]
    elif field in {"left_gap", "right_gap"}:
        right = field == "right_gap"
        nodes = (
            (
                [
                    *_paired(0.55, 2.8, (1.675,)),
                    _fixed(-4.675, 0.55),
                    _line(
                        2.8,
                        1.6,
                        4.675,
                        1.6,
                        stroke_opacity=0.28,
                        linecap="butt",
                        data_end_context="cohesive overhang; excluded from spacer",
                    ),
                ]
            )
            if right
            else (
                [
                    *_paired(-2.8, -0.55, (-1.675,)),
                    _fixed(-0.55, 4.675),
                    _line(
                        -4.675,
                        -1.6,
                        -2.8,
                        -1.6,
                        stroke_opacity=0.28,
                        linecap="butt",
                        data_end_context="cohesive overhang; excluded from spacer",
                    ),
                ]
            )
        )
    elif field in {"basal_pairs", "foldback_pairs"}:
        nodes = _paired(-4, 4, (-2.8, 0, 2.8))
    elif field in {"loop", "loop_nt"}:
        nodes = _loop()
    elif field in {"left_word", "right_word", "left_polarity", "right_polarity"}:
        nodes = _end(field.startswith("right"))
    elif field in {"basal_method", "foldback_method", "release_method"}:
        nodes = _enzyme(field == "release_method")
    elif "tail" in field or field.endswith("unpaired_nt"):
        nodes = [_line(-4, 0, 4, 0), _line(-4, 0, -4, 2)]
        nodes += [
            _node("circle", cx=x, cy=0, r=0.65, fill=PALE, stroke=INK, stroke_width=0.6)
            for x in (-2, 0, 2)
        ]
    else:
        nodes = [
            _node(
                "rect",
                x=-4,
                y=-2,
                width=8,
                height=4,
                rx=0.6,
                fill=PALE,
                stroke=INK,
                stroke_width=0.7,
            )
        ]
        nodes += [_node("circle", cx=x, cy=0, r=0.3, fill=INK) for x in (-2, 0, 2)]
    return {"view_box": [-6, -4, 12, 8], "nodes": nodes}


def comparison_glyph_presentation(keys: Iterable[str]) -> dict[str, Any]:
    """Describe field types, never measured values or nominal-code magnitudes.

    This display permutation leaves the source comparison vector untouched.
    Additional fields retain their input order after the familiar field sequence.
    Nodes use only inert SVG geometry, shared verbatim with the browser renderer.
    """
    fields = list(keys)
    if len(set(fields)) != len(fields):
        raise ValueError("Comparison display fields must be distinct.")
    order: list[str] = []
    for block in ("shape", "sequences", "interfaces", "processing"):
        order.extend(key for key in _ORDER if key in fields and key.startswith(block + "."))
        order.extend(key for key in fields if key.startswith(block + ".") and key not in order)
    order.extend(key for key in fields if key not in order)
    bands = []
    for key, label, blocks, fill in (
        ("shape", "Geometry", ("shape",), "#e5edea"),
        ("sequence", "Sequences", ("sequences", "interfaces"), "#dfebf3"),
        ("processing", "Enzymes", ("processing",), "#e4eee8"),
        ("other", "Inputs", (), "#e5edea"),
    ):
        members = [field for field in order if field.split(".")[0] in blocks]
        if key == "other":
            members = [
                field
                for field in order
                if field.split(".")[0] not in {"shape", "sequences", "interfaces", "processing"}
            ]
        if members:
            bands.append({"key": key, "label": label, "fill": fill, "fields": members})
    return {
        "display": "schematic-glyphs",
        "display_order": order,
        "field_pitch": 13.2,
        "font_size": 7.2,
        "label_angle": -45,
        "schema_groups": bands,
        "glyphs": {key: _glyph(key) for key in fields},
    }
