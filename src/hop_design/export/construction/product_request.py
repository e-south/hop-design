"""Render the boundary between authored intent and unevaluated construction inputs."""

from hop_design.models.construction.product_request import ProductRequest


def render_product_request(request: ProductRequest) -> str:
    lines = [
        "# Construction request",
        "",
        "Prepared input; not a verified construction. No search has run.",
        "",
        "## Required",
        "",
        f"Endpoint: {request.endpoint.value}.",
        f"Stem arm: {request.stem_arm} (5-prime to 3-prime).",
    ]
    if request.ends is not None:
        for side in ("left", "right"):
            end = getattr(request.ends, side)
            lines.append(
                f"{side.capitalize()} end: {end.cohesive_end_sequence} on its own protruding "
                f"strand (5-prime to 3-prime); {end.overhang_end.value} overhang; "
                f"{end.payload_end_offset_bp} paired bp to payload; "
                f"{end.orientation.value} recognition-site orientation."
            )
    else:
        lines.append("No downstream release-end requirements for this endpoint.")
    scaffold = request.whole_route_constraints.hairpin_scaffold
    if scaffold is not None:
        lines.append("Hairpin scaffold requirements (checked on the joined molecule):")
        for name, label in (
            ("open_side_paired_positions", "Open-side paired positions"),
            ("loop_side_paired_bp", "Loop-side paired extension (bp)"),
            ("loop_nt", "Loop size (nt)"),
        ):
            allowed = getattr(scaffold, name)
            if allowed is not None:
                lines.append(f"{label}: {allowed.minimum} to {allowed.maximum}, inclusive.")
        lines.append("These requirements do not enlarge or relax the declared search domain.")
    foldback = request.foldback.geometry
    lines.append(
        f"Foldback: paired-arm domain {list(foldback.annealing_arm_lengths_bp)} bp; "
        f"cap domain {list(foldback.loop_lengths_nt)} nt; "
        f"join-displacement domain {list(foldback.junction_offsets_nt)} nt."
    )
    if request.basal is not None:
        basal = request.basal.geometry
        lines.append(
            f"Basal: nick-offset domain {list(basal.nick_offsets_nt)} nt; "
            f"minimum adapter association {basal.minimum_adapter_annealing_nt} nt; "
            "position-specific pairing permissions remain in the authored request."
        )
    if request.hairpin_basal_component is not None:
        component = request.hairpin_basal_component
        lines.append(
            f"Exact hairpin basal component: left arm {component.left_arm}; "
            f"right arm {component.right_arm}; each written 5-prime to 3-prime. "
            "These terminal arms are not a downstream basal-processing request."
        )
    lines.append(
        "Source material permission: "
        f"{request.materialization.source_preparation.source_ssdna.mode.value}."
    )
    if request.source_cleanup is not None:
        cleanup = request.source_cleanup
        lines.append(
            f"Source cleanup: discarded fragments at most {cleanup.absolute_maximum_nt} nt "
            f"(preferred maximum {cleanup.preferred_maximum_nt} nt). Request discovery "
            "must verify the selected nicking program and exact retained strands for "
            "each source context. The expanded construction input alone has no cleanup certificate."
        )
    lines += [
        "Authored geometry, material chemistry, enzyme permissions and bounds are preserved.",
        "Preferences never replace required ends or relax material constraints.",
        "",
        "## Derived",
        "",
        "Payload boundary coordinates, repeated local payload records and catalog bindings.",
        *(
            ["The selected basal end projection copies the corresponding product requirement."]
            if request.release is not None
            else []
        ),
        *(
            [
                "Required left-end bases propagated to declared source contacts (position from "
                "ligation, base): " + str(list(request.implied_source_contact_bases())) + "."
            ]
            if request.implied_source_contact_bases()
            else [
                "No additional local source-base propagation applies to this geometry; "
                "complete-route end requirements remain mandatory."
            ]
        ),
        "Paired sequence and exact oligos are derived later by the existing construction engine.",
        "",
        "## Unresolved",
        "",
        "Feasibility, actual end words, exact materials and search coverage await discovery "
        "and complete-route verification. Local witnesses must be selected explicitly.",
        "Hairpin execution requires an explicit hairpin_basal_component; translation "
        "does not invent terminal sequence or borrow a downstream insert design.",
    ]
    return "\n".join(lines) + "\n"
