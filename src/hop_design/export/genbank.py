"""Deterministic GenBank projection for HOP-owned physical duplex products."""

from __future__ import annotations

from hop_design.models.linear_source_method import LinearSourceMultinickHairpinPcrPlan
from hop_design.models.method import BindingOrientation, ProcessMaterialRole


def _location(start: int, end: int, *, complement: bool = False) -> str:
    value = f"{start + 1}..{end}"
    return f"complement({value})" if complement else value


def _qualifier(name: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'                     /{name}="{escaped}"'


def _feature(
    kind: str,
    location: str,
    *qualifiers: tuple[str, str],
) -> list[str]:
    lines = [f"     {kind:<16}{location}"]
    lines.extend(_qualifier(name, value) for name, value in qualifiers)
    return lines


def _origin_lines(sequence: str) -> list[str]:
    lines = ["ORIGIN"]
    lower = sequence.lower()
    for offset in range(0, len(lower), 60):
        chunk = lower[offset : offset + 60]
        groups = " ".join(chunk[index : index + 10] for index in range(0, len(chunk), 10))
        lines.append(f"{offset + 1:>9} {groups}")
    return lines


def render_hairpin_pcr_genbank(plan: LinearSourceMultinickHairpinPcrPlan) -> bytes:
    """Render the exact PCR duplex; destination assembly remains unasserted."""
    duplex = plan.hairpin_pcr_duplex
    sequence = duplex.top_strand.sequence
    selected_ids = set(plan.length_selected_fragment_set.retained_fragment_ids)
    retained = tuple(
        fragment
        for fragment in plan.denatured_fragment_set.fragments
        if fragment.fragment_id in selected_ids
    )
    top = next(fragment for fragment in retained if fragment.precursor_strand == "top")
    bottom = next(fragment for fragment in retained if fragment.precursor_strand == "bottom")
    adapter = next(
        material
        for material in plan.materials.materials
        if material.role is ProcessMaterialRole.LIGATION_ADAPTER
    )
    top_end = len(top.sequence)
    bottom_end = top_end + len(bottom.sequence)

    lines = [
        f"LOCUS       HOP_METHOD{len(sequence):>17} bp    ds-DNA     linear   SYN 01-JAN-1980",
        "DEFINITION  HOP hairpin-PCR duplex.",
        f"ACCESSION   {plan.request_digest.removeprefix('sha256:')[:16]}",
        "VERSION     1",
        "KEYWORDS    .",
        "SOURCE      synthetic DNA construct",
        "  ORGANISM  synthetic DNA construct",
        "FEATURES             Location/Qualifiers",
    ]
    lines.extend(
        _feature(
            "source",
            _location(0, len(sequence)),
            ("state", "hairpin-pcr-duplex"),
            ("topology", "linear"),
            ("strandedness", "double"),
        )
    )
    for start, end, label in (
        (0, top_end, "selected-top-fragment"),
        (top_end, bottom_end, "selected-bottom-fragment"),
        (bottom_end, len(sequence), adapter.material_id),
    ):
        lines.extend(_feature("misc_feature", _location(start, end), ("component", label)))
    for binding in duplex.primer_bindings:
        lines.extend(
            _feature(
                "primer_bind",
                _location(
                    binding.template_span.start.offset,
                    binding.template_span.end.offset,
                    complement=(binding.orientation is BindingOrientation.REVERSE_COMPLEMENT_5TO3),
                ),
                ("primer_id", binding.primer_id),
            )
        )
    for site in plan.restriction_digest_product.sites:
        lines.extend(
            _feature(
                "misc_feature",
                _location(site.site_span.start.offset, site.site_span.end.offset),
                ("restriction_agent", site.agent_id),
                ("site_orientation", site.orientation),
            )
        )
    projection = plan.restriction_digest_product.hairpin_encoding_projection
    lines.extend(
        _feature(
            "misc_feature",
            _location(
                projection.source_span.start.offset,
                projection.source_span.end.offset,
                complement=(projection.orientation is BindingOrientation.REVERSE_COMPLEMENT_5TO3),
            ),
            ("projection", "hairpin-encoding"),
            ("sequence_digest", projection.sequence_digest),
        )
    )
    lines.extend(_origin_lines(sequence))
    lines.append("//")
    return ("\n".join(lines) + "\n").encode()


__all__ = ["render_hairpin_pcr_genbank"]
