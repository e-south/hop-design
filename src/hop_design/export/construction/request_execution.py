"""Explain bounded request outcomes without promoting a diagnosis into a repair."""

from hop_design.models.construction import ConstructionEndpoint

from .handoff.site_conflicts import site_conflict_lines
from .labels import endpoint_label


def render_request_context(
    *, endpoint: str, payload_nt: int, ends: dict[str, dict[str, object]] | None
) -> str:
    lines = [
        f"Requested: {endpoint_label(ConstructionEndpoint(endpoint))}; stem arm {payload_nt} nt."
    ]
    if ends is not None:
        for side in ("left", "right"):
            end = ends[side]
            polarity = "5-prime" if end["overhang_end"] == "five_prime" else "3-prime"
            lines.append(
                f"{side.capitalize()} (site orientation: {end['orientation']}): "
                f"5'-{end['cohesive_end_sequence']}-3'; {polarity} overhang; "
                f"{end['payload_end_offset_bp']} bp paired flank."
            )
    return "\n".join(lines) + "\n\n"


def render_local_stop(
    *, family: str, count: int, status: str, termination: str, rejections: dict[str, int]
) -> str:
    if count > 1:
        meaning = (
            f"{count} {family} witnesses were recorded. The sole-witness policy cannot "
            "choose among them. Inspect the saved local choices and explicitly select "
            "a realization for construction continue with the saved inputs/request.json. "
            "If another required local family was not searched, discover it from its saved input."
        )
    elif status == "infeasible":
        meaning = (
            f"No {family} witness exists within the exhausted local domain. "
            "A complete route requiring this local component cannot proceed under these inputs. "
            "Compare an explicitly edited request if different ends, enzymes or geometry "
            "would be acceptable."
        )
    else:
        meaning = (
            f"No {family} witness was recorded before the search stopped. "
            "Feasibility is unresolved. An explicitly larger search bound can investigate "
            "the remaining domain; it does not guarantee a witness."
        )
    reasons = (
        ", ".join(f"{code}: {number}" for code, number in rejections.items()) or "none recorded"
    )
    return (
        "# Construction request outcome\n\n"
        f"{meaning}\n\n"
        f"Rejected local candidates by recorded reason: {reasons}. "
        "These counts describe examined candidates.\n\n"
        f"Search termination: {termination}. The saved {family}/result.json records "
        "the exact request, coverage and diagnostics. "
        "Downstream construction was not evaluated.\n\n"
        "An alternative request is a new comparison, not a uniquely necessary repair. "
        "No end, contact, enzyme or material permission was relaxed.\n"
    )


def render_complete_outcome(
    *,
    status: str,
    accepted: int,
    rejections: list[str],
    preparation_constraints: list[dict[str, object]] | None = None,
    scaffold_mismatches: list[dict[str, object]] | None = None,
    actionable_sites: list[dict[str, object]] | None = None,
) -> str:
    preparation = (
        "Read handoff/report.md and oligos.csv for the accepted preparation."
        if accepted == 1
        else "Multiple preparations were recorded; explicitly select one from construction/."
        if accepted > 1
        else "No preparation was accepted for this selected combination."
    )
    reasons = ", ".join(rejections) if rejections else "none"
    constraints = "".join(
        f"Violated preparation constraint ({item['stage']}): {item['field']}; "
        f"requested {item['requested']}; requirement {item['requirement']}; "
        f"available/evaluated {item['available']}. "
        f"{item['message']}\n\n"
        for item in preparation_constraints or []
    )
    for item in scaffold_mismatches or []:
        required = item["required"]
        assert isinstance(required, dict)
        constraints += (
            f"Hairpin {item['dimension']}: "
            f"requested {required['minimum']} to {required['maximum']}; "
            f"observed {item['observed']} in the joined hairpin. "
            "This candidate is not selectable under the authored requirement.\n\n"
        )
    constraints += "\n\n".join(site_conflict_lines(actionable_sites or []))
    return (
        "# Construction request outcome\n\n"
        f"Selected continuation: {status}. {preparation}\n\n"
        f"Recorded rejection reasons: {reasons}.\n\n"
        f"{constraints}"
        "This outcome covers the selected local combination. "
        "Local search coverage and termination reasons are retained in summary.json. "
        "The construction/ bundle retains complete-route accounting and diagnostics.\n\n"
        "Compare explicitly edited material, contact or geometry permissions if appropriate; "
        "the saved request retains every requirement.\n"
    )
