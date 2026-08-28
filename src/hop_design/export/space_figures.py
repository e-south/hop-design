"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/space_figures.py

Renders deterministic generic SVG projections from a verified design set.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import html
import math
from collections.abc import Mapping

from hop_design.models.design_space import HairpinDesignSet, SubstrateSpaceSpec
from hop_design.models.sequence import iupac_bases

_BASE_ORDER = ("A", "C", "G", "T")
_INK = "#17211d"
_MUTED = "#5b6661"
_RULE = "#cbd3cf"
_ACCENT = "#176b54"
_VARIABLE = "#dcefe8"
_WASH = "#f3f6f4"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _svg_document(*, width: int, height: int, title: str, body: str) -> bytes:
    markup = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
viewBox="0 0 {width} {height}" role="img" aria-labelledby="figure-title figure-description">
<title id="figure-title">{_escape(title)}</title>
<desc id="figure-description">Generic HOP projection from a verified digital design set.</desc>
<style>
text {{ fill:{_INK}; font-family:Arial, Helvetica, sans-serif; }}
.title {{ font-size:30px; font-weight:700; }}
.subtitle {{ font-size:17px; fill:{_MUTED}; }}
.label {{ font-size:14px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
.body {{ font-size:16px; }}
.sequence {{ font:600 17px ui-monospace, SFMono-Regular, Menlo, monospace; }}
.tile-sequence {{ font:600 12px ui-monospace, SFMono-Regular, Menlo, monospace; }}
.small {{ font-size:13px; fill:{_MUTED}; }}
.rule {{ stroke:{_RULE}; stroke-width:1; }}
.accent {{ fill:{_ACCENT}; }}
</style>
<rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>
"""
    return markup.encode("utf-8")


def _payload_parts(spec: SubstrateSpaceSpec) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    payload = "".join(segment.fixed or segment.variable or "" for segment in spec.payload)
    kinds = tuple(
        kind
        for segment in spec.payload
        for kind in (
            ("fixed",) * len(segment.fixed)
            if segment.fixed is not None
            else ("variable",) * len(segment.variable or "")
        )
    )
    domain_labels = tuple(
        f"{symbol}=" + "/".join(base for base in _BASE_ORDER if base in iupac_bases(symbol))
        for segment in spec.payload
        if segment.variable is not None
        for symbol in segment.variable
    )
    return payload, kinds, domain_labels


def render_substrate_space_svg(
    spec: SubstrateSpaceSpec,
    design_set: HairpinDesignSet,
    member_encodings: Mapping[str, tuple[str, str]],
    *,
    defaults_display_name: str,
    defaults_anatomy_summary: str,
) -> bytes:
    """Render the authored rule, paired arm, cardinality, and one exact encoding."""
    title = "Authored and derived positions define the paired substrate space."
    payload, kinds, domain_labels = _payload_parts(spec)
    paired = design_set.members[0].derived_paired_payload[::-1]
    first = design_set.members[0]
    _, encoding = member_encodings[first.member_bundle_id]
    start_x = 72
    base_width = min(54, max(28, 900 // len(payload)))
    base_boxes: list[str] = []
    for index, (authored, opposite, kind) in enumerate(zip(payload, paired, kinds, strict=True)):
        x = start_x + index * base_width
        fill = _VARIABLE if kind == "variable" else "#ffffff"
        stroke = _ACCENT if kind == "variable" else _INK
        dash = ' stroke-dasharray="5 4"' if kind == "variable" else ""
        base_boxes.append(
            f'<g data-payload-position="{index + 1}" data-kind="{kind}">'
            f'<rect x="{x}" y="210" width="{base_width - 4}" height="36" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>'
            f'<text x="{x + (base_width - 4) / 2}" y="234" text-anchor="middle" '
            f'class="sequence">{_escape(authored)}</text>'
            f'<line x1="{x + (base_width - 4) / 2}" y1="248" '
            f'x2="{x + (base_width - 4) / 2}" y2="274" class="rule"/>'
            f'<rect x="{x}" y="276" width="{base_width - 4}" height="36" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>'
            f'<text x="{x + (base_width - 4) / 2}" y="300" text-anchor="middle" '
            f'class="sequence">{_escape(opposite)}</text></g>'
        )
    domain_text = " · ".join(domain_labels) if domain_labels else "No variable positions"
    question = spec.question or "Rule-defined paired DNA substrate space"
    paired_display_note = "3-prime paired display; stored sequence is the reverse complement"
    accounting = (
        f"Exhaustive digital accounting · {design_set.unique_designs} unique · "
        f"{design_set.duplicate_count} duplicates"
    )
    encoding_boundary = "The encoding is digitally derived; no folded or physical state is implied."
    body = f"""
<text x="72" y="72" class="title">{_escape(title)}</text>
<text x="72" y="112" class="subtitle">{_escape(question)}</text>
<line x1="72" y1="142" x2="1128" y2="142" class="rule"/>
<text x="72" y="184" class="label">Authored payload and derived pairing</text>
<text x="72" y="205" class="small">5-prime authored arm</text>
{"".join(base_boxes)}
<text x="72" y="334" class="small">{_escape(paired_display_note)}</text>
<text x="72" y="376" class="body">Variable domains: {_escape(domain_text)}</text>
<text x="72" y="410" class="body">The paired arm is derived by reverse complement.</text>
<text x="72" y="454" class="label">Complete declared space</text>
<text x="72" y="490" class="title">{design_set.theoretical_cardinality} exact designs</text>
<text x="72" y="520" class="subtitle">{_escape(accounting)}</text>
<text x="72" y="570" class="label">Selected fixed hairpin context</text>
<text x="72" y="603" class="body">{_escape(defaults_display_name)}</text>
<text x="72" y="630" class="small">{_escape(defaults_anatomy_summary)}</text>
<text x="72" y="680" class="label">One expanded exact member</text>
<text x="72" y="714" class="sequence">Payload: {_escape(first.exact_payload)}</text>
<text x="72" y="744" class="sequence">Paired: {_escape(first.derived_paired_payload)}</text>
<text x="72" y="774" class="sequence">Encoding: {_escape(encoding)}</text>
<text x="72" y="814" class="small">{_escape(encoding_boundary)}</text>
"""
    return _svg_document(width=1200, height=860, title=title, body=body)


def render_design_set_svg(design_set: HairpinDesignSet) -> bytes:
    """Render every exact member in deterministic, explicitly non-ranked order."""
    title = "Complete digital design-set diagnostic"
    count = len(design_set.members)
    columns = min(16, max(2, math.ceil(math.sqrt(count))))
    tile_width = 64
    tile_height = 64
    gap = 6
    grid_width = columns * tile_width + (columns - 1) * gap
    start_x = (1200 - grid_width) // 2
    start_y = 250
    tiles: list[str] = []
    for index, record in enumerate(design_set.members):
        row, column = divmod(index, columns)
        x = start_x + column * (tile_width + gap)
        y = start_y + row * (tile_height + gap)
        assignment = ";".join(f"{item.position}={item.base}" for item in record.variable_assignment)
        assignment_bases = "".join(item.base for item in record.variable_assignment)
        tiles.append(
            f'<g data-design-member="true" data-ordinal="{record.canonical_ordinal}" '
            f'data-assignment="{_escape(assignment)}" '
            f'data-payload="{_escape(record.exact_payload)}" '
            f'data-disposition="{record.disposition}">'
            f'<rect x="{x}" y="{y}" width="{tile_width}" height="{tile_height}" rx="3" '
            f'fill="{_VARIABLE if record.disposition == "canonical" else _WASH}" '
            f'stroke="{_ACCENT if record.disposition == "canonical" else _MUTED}"/>'
            f'<text x="{x + 8}" y="{y + 20}" class="small">{record.canonical_ordinal}</text>'
            f'<text x="{x + tile_width / 2}" y="{y + 44}" text-anchor="middle" '
            f'class="tile-sequence">{_escape(assignment_bases)}</text></g>'
        )
    rows = math.ceil(count / columns)
    height = start_y + rows * (tile_height + gap) + 150
    accounting = (
        f"{design_set.enumerated_assignments} of {design_set.theoretical_cardinality} "
        f"assignments · {design_set.unique_designs} unique · "
        f"{design_set.duplicate_count} duplicates"
    )
    metadata_note = (
        "Each tile carries its exact assignment, payload, disposition, and member ordinal "
        "as SVG metadata."
    )
    body = f"""
<text x="72" y="72" class="title">Complete digital design-set diagnostic</text>
<text x="72" y="108" class="subtitle">Every assignment is shown in deterministic,
non-ranked order.</text>
<text x="72" y="148" class="subtitle">{_escape(accounting)}</text>
<line x1="72" y1="178" x2="1128" y2="178" class="rule"/>
<text x="72" y="208" class="body">Ordinal is deterministic replay order, not rank.</text>
{"".join(tiles)}
<text x="72" y="{height - 62}" class="small">{_escape(metadata_note)}</text>
"""
    return _svg_document(width=1200, height=height, title=title, body=body)


def render_scientific_receipt_svg(design_set: HairpinDesignSet) -> bytes:
    """Render complete accounting and the manifest-backed evidence boundary."""
    title = "Digital evidence boundary"
    claim_labels = {
        "space_accounting": "Substrate-space accounting",
        "digital_design": "Exact digital designs",
        "named_method": "Named construction method",
        "destination_compatibility": "Destination compatibility",
        "physical_construction": "Physical construction",
        "quality_control": "Quality control",
        "biological_activity": "Biological activity",
    }
    rows: list[str] = []
    for index, (dimension, claim) in enumerate(design_set.claim_status):
        claim_data = claim.model_dump(mode="json")
        status = claim_data["status"]
        basis = claim_data.get("basis", "")
        y = 404 + index * 42
        rows.append(
            f'<g data-evidence-dimension="{dimension}" data-status="{status}" '
            f'data-basis="{_escape(basis)}">'
            f'<text x="72" y="{y}" class="body">{_escape(claim_labels[dimension])}</text>'
            f'<text x="590" y="{y}" class="body">{_escape(status.replace("_", " "))}</text>'
            f'<line x1="72" y1="{y + 14}" x2="1128" y2="{y + 14}" class="rule"/></g>'
        )
    assignment_count = (
        f"{design_set.enumerated_assignments}/{design_set.theoretical_cardinality} "
        "exact assignments"
    )
    accounting = (
        f"{design_set.unique_designs} unique designs · {design_set.duplicate_count} "
        "duplicates · digital verification passed"
    )
    evidence_boundary = "No physical construction, QC, or activity record is attached."
    handoff_note = (
        "CSV and FASTA provide sequence handoff; bundle/ remains the verified digital authority."
    )
    body = f"""
<text x="72" y="72" class="title">Digital evidence boundary</text>
<text x="72" y="108" class="subtitle">Verified derivation and absent experimental
evidence remain distinct.</text>
<line x1="72" y1="140" x2="1128" y2="140" class="rule"/>
<text x="72" y="188" class="label">Complete digital handoff</text>
<text x="72" y="232" class="title">{_escape(assignment_count)}</text>
<text x="72" y="268" class="body">{_escape(accounting)}</text>
<text x="72" y="310" class="small">Design-set identity</text>
<text x="72" y="338" class="sequence">{_escape(design_set.design_set_id)}</text>
<text x="72" y="378" class="label">Evidence carried by the verified manifest</text>
{"".join(rows)}
<text x="72" y="{404 + len(rows) * 42 + 38}" class="body">{_escape(evidence_boundary)}</text>
<text x="72" y="{404 + len(rows) * 42 + 72}" class="small">{_escape(handoff_note)}</text>
"""
    height = 404 + len(rows) * 42 + 120
    return _svg_document(width=1200, height=height, title=title, body=body)


__all__ = [
    "render_design_set_svg",
    "render_scientific_receipt_svg",
    "render_substrate_space_svg",
]
