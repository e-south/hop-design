"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/spaces.py

Renders regenerable scientist-facing projections from a verified design set.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import html

from hop_design.models.design_space import HairpinDesignSet, SubstrateSpaceSpec
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

_BASE_ORDER = ("A", "C", "G", "T")
_CLAIM_LABELS = {
    "space_accounting": "Substrate-space accounting",
    "digital_design": "Exact digital designs",
    "named_method": "Named construction method",
    "destination_compatibility": "Destination compatibility",
    "physical_construction": "Physical construction",
    "quality_control": "Quality control",
    "biological_activity": "Biological activity",
}


def render_review_html(
    spec: SubstrateSpaceSpec,
    design_set: HairpinDesignSet,
    *,
    verified_member_count: int,
) -> bytes:
    """Render one offline scientific review of a complete design set."""
    if verified_member_count != design_set.unique_designs:
        raise ValueError("Review requires every unique verified member.")
    rendered_rows: list[str] = []
    for record in design_set.members:
        assignment = html.escape(
            "; ".join(f"{item.position}={item.base}" for item in record.variable_assignment)
        )
        search_text = html.escape(
            " ".join(
                (
                    str(record.canonical_ordinal),
                    assignment,
                    record.exact_payload,
                    record.derived_paired_payload,
                    record.disposition,
                )
            ).lower()
        )
        rendered_rows.append(
            f'<tr data-design-row="true" data-search="{search_text}">'
            f"<td>{record.canonical_ordinal}</td>"
            f"<td><code>{assignment}</code></td>"
            f"<td><code>{record.exact_payload}</code></td>"
            f"<td><code>{record.derived_paired_payload}</code></td>"
            f"<td>{record.exact_hairpin_length}</td>"
            f"<td>{record.disposition}</td>"
            "</tr>"
        )
    rows = "".join(rendered_rows)

    payload = "".join(segment.fixed or segment.variable or "" for segment in spec.payload.segments)
    position_kinds = tuple(
        kind
        for segment in spec.payload.segments
        for kind in (
            ("fixed",) * len(segment.fixed)
            if segment.fixed is not None
            else ("variable",) * len(segment.variable or "")
        )
    )
    aligned_pair = reverse_complement_iupac(payload)[::-1]
    base_pairs = "".join(
        f'<div class="base-pair" aria-label="Position {position}: {kind}">'
        f'<span class="base {kind}">{authored}</span>'
        '<span class="pair-line" aria-hidden="true">│</span>'
        f'<span class="base {kind}">{paired}</span>'
        "</div>"
        for position, (authored, paired, kind) in enumerate(
            zip(payload, aligned_pair, position_kinds, strict=True), start=1
        )
    )
    segment_labels: list[str] = []
    for index, segment in enumerate(spec.payload.segments, start=1):
        segment_kind = "fixed" if segment.fixed is not None else "variable"
        name = segment.name or f"{segment_kind} segment {index}"
        if segment.fixed is not None:
            description = "fixed"
        else:
            domains = tuple(
                "/".join(base for base in _BASE_ORDER if base in iupac_bases(symbol))
                for symbol in segment.variable or ""
            )
            domain_text = domains[0] if len(set(domains)) == 1 else ", ".join(domains)
            description = f"variable {domain_text}"
        segment_labels.append(f"<li>{html.escape(name)} · {html.escape(description)}</li>")
    segments = "".join(segment_labels)

    variable_count = len(design_set.members[0].variable_assignment)
    variable_label = "position" if variable_count == 1 else "positions"
    summary_title = (
        f"{design_set.unique_designs} exact hairpin designs from "
        f"{variable_count} variable paired {variable_label}"
    )
    question = ""
    if spec.context is not None and spec.context.question is not None:
        question = f'<p class="question">{html.escape(spec.context.question)}</p>'
    claim_rows: list[str] = []
    for dimension, claim in design_set.claim_status:
        claim_data = claim.model_dump(mode="json")
        status = claim_data["status"]
        basis = claim_data.get("basis")
        basis_attribute = "" if basis is None else f' data-basis="{html.escape(basis)}"'
        basis_text = "—" if basis is None else basis.replace("_", " ")
        claim_rows.append(
            f'<tr data-claim="{dimension}" data-status="{status}"{basis_attribute}>'
            f"<td>{_CLAIM_LABELS[dimension]}</td>"
            f"<td>{status.replace('_', ' ').capitalize()}</td>"
            f"<td>{basis_text}</td>"
            "</tr>"
        )
    rendered_claim_rows = "".join(claim_rows)
    markup = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>{html.escape(spec.name)} · HOP Design</title>
<style>
:root {{
  color-scheme: light;
  --ink:#18211d;
  --muted:#58615d;
  --rule:#ccd2cf;
  --accent:#176b54;
  --wash:#f2f5f3;
  --variable-wash:#e5f3ee;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  color:var(--ink);
  background:#fff;
  font:16px/1.55 system-ui,-apple-system,sans-serif;
}}
main {{ width:min(calc(100% - 2rem), 72rem); margin:0 auto; padding:3rem 0 5rem; }}
h1,h2 {{ line-height:1.15; letter-spacing:-.02em; }}
h1 {{ max-width:18ch; font-size:clamp(2rem,5vw,4rem); margin:0 0 1rem; }}
h2 {{ font-size:1.35rem; margin:0 0 1rem; }}
section {{ padding:2rem 0; border-top:1px solid var(--rule); }}
.lede {{ max-width:62ch; font-size:1.15rem; }}
.question {{ max-width:62ch; color:var(--muted); }}
.boundary {{
  max-width:70ch;
  padding:1rem 1.2rem;
  border-left:.3rem solid var(--accent);
  background:var(--wash);
}}
.segment-key {{ display:flex; flex-wrap:wrap; gap:.35rem 1.5rem; padding:0; }}
.segment-key li {{ list-style:none; }}
.duplex-wrap {{ overflow-x:auto; padding:.4rem 0 1rem; }}
.duplex {{ display:flex; width:max-content; gap:.15rem; margin:.7rem 0; }}
.base-pair {{
  display:flex;
  flex-direction:column;
  align-items:center;
  font:700 1.1rem/1.25 ui-monospace,monospace;
}}
.base {{
  min-width:1.65rem;
  padding:.15rem .25rem;
  text-align:center;
  border:1px solid var(--ink);
}}
.base.variable {{
  color:var(--accent);
  background:var(--variable-wash);
  border:2px dashed var(--accent);
}}
.pair-line {{ height:1.25rem; color:var(--muted); }}
.orientation {{ display:flex; justify-content:space-between; width:max-content; min-width:100%; }}
.facts {{ display:flex; flex-wrap:wrap; gap:1rem 2.5rem; margin:1rem 0; }}
.fact strong {{ display:block; font-size:1.6rem; }} .fact span {{ color:var(--muted); }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; }}
#design-table {{ min-width:56rem; }}
th,td {{
  padding:.7rem .6rem;
  text-align:left;
  border-bottom:1px solid var(--rule);
  white-space:nowrap;
}}
th {{ font-size:.83rem; text-transform:uppercase; letter-spacing:.04em; }}
code {{ font-family:ui-monospace,monospace; }}
details {{ margin-top:1rem; }}
.filter {{ display:flex; flex-wrap:wrap; align-items:center; gap:.6rem; margin:0 0 1rem; }}
.filter input {{ min-width:min(100%, 22rem); padding:.55rem .65rem; font:inherit; }}
@media (max-width: 768px) {{
  main {{ width:min(calc(100% - 1.25rem), 72rem); padding-top:1.5rem; }}
  h1 {{ font-size:clamp(2rem,11vw,3rem); }}
  section {{ padding:1.5rem 0; }}
  .facts {{ gap:.75rem 1.5rem; }}
}}
@media print {{ main {{ width:100%; padding:0; }} .table-wrap {{ overflow:visible; }} }}
</style>
</head>
<body><main>
<header>
<p>HOP Design · verified digital design set</p>
<h1>{summary_title}</h1>
<p class="lede">
  The declared substrate space was exhaustively expanded into exact hairpin encodings.
</p>
{question}
<p class="boundary">
  <strong>Compiled means digitally derived and verified.</strong>
  It does not mean the molecules were physically constructed or assayed.
</p>
</header>
<section><h2>Substrate-space anatomy</h2>
<ul class="segment-key">{segments}</ul>
<figure>
<div class="duplex-wrap" role="img" aria-label="Authored and automatically paired payloads">
  <div class="orientation"><span>5&prime;</span><span>3&prime;</span></div>
  <div class="duplex">{base_pairs}</div>
  <div class="orientation"><span>3&prime;</span><span>5&prime;</span></div>
</div>
<figcaption>
  The paired arm is displayed 3&prime;&rarr;5&prime; beneath the authored arm;
  its stored 5&prime;&rarr;3&prime; sequence is its reverse complement,
  <code>{design_set.members[0].derived_paired_payload}</code>.
</figcaption>
</figure>
<p>
  Pairing is derived automatically using
  <code>{html.escape(spec.hairpin.defaults_ref)}</code>.
</p>
</section>
<section><h2>Space accounting</h2><div class="facts">
<div class="fact"><strong>{design_set.theoretical_cardinality}</strong>
<span>theoretical assignments</span></div>
<div class="fact"><strong>{design_set.unique_designs}</strong>
<span>unique exact designs</span></div>
<div class="fact"><strong>{design_set.duplicate_count}</strong>
<span>duplicates</span></div>
<div class="fact"><strong>Complete</strong><span>coverage</span></div>
</div></section>
<section><h2>Evidence</h2><div class="table-wrap"><table>
<thead><tr><th scope="col">Evidence dimension</th><th scope="col">Status</th>
<th scope="col">Basis</th></tr></thead><tbody>
{rendered_claim_rows}
</tbody></table></div></section>
<section><h2>Design table</h2>
<div class="filter">
  <label for="design-search">Filter exact designs</label>
  <input id="design-search" type="search" autocomplete="off"
         placeholder="Assignment or sequence" aria-controls="design-table">
</div>
<div class="table-wrap"><table id="design-table">
<thead><tr><th scope="col">Ordinal</th><th scope="col">Assignment</th>
<th scope="col">Exact payload</th><th scope="col">Derived paired payload</th>
<th scope="col">Hairpin length</th><th scope="col">Disposition</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
<section><h2>Handoff</h2><p>
  <code>designs.csv</code> is the sequence index;
  <code>sequences.fasta</code> is the sequence handoff;
  <code>bundle/</code> is the verified digital authority; and
  <code>source.yaml</code> records the authored specification.
</p>
<details><summary>Technical details</summary>
<p>Design-set ID: <code>{html.escape(design_set.design_set_id)}</code></p>
<p>Manifest digest: <code>{design_set.manifest_digest}</code></p>
</details></section>
</main>
<script>
const search = document.querySelector("#design-search");
const rows = document.querySelectorAll('[data-design-row="true"]');
search.addEventListener("input", () => {{
  const query = search.value.trim().toLowerCase();
  rows.forEach((row) => {{
    row.hidden = !row.dataset.search.includes(query);
  }});
}});
</script>
</body></html>
"""
    return markup.encode("utf-8")


__all__ = [
    "render_review_html",
]
