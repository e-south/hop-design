"""Regional preservation and plain comparisons over recorded molecular coordinates."""

from hop_design.models.construction.variants.parameters import parameter_definition

from .types import ChoiceSource, Record


class NoLoopAlternative(ValueError):
    """The verified membership contains no eligible different loop."""


def loop_alternatives(
    choices: ChoiceSource,
    current: Record,
    history: tuple[str, ...],
    *,
    candidates: tuple[str, ...] | None = None,
) -> Record:
    if not history:
        raise ValueError("Select a reference preparation before asking for another loop.")
    rows = {p["materialized_realization_id"]: p for p in current["paths"]}
    if history[-1] not in rows:
        raise ValueError("Loop reference is outside this recorded pool.")
    if candidates is not None and set(candidates) - rows.keys():
        raise ValueError("Loop candidates are outside this recorded pool.")
    word = rows[history[-1]]["values"].get("loop_word")
    if not isinstance(word, str):
        raise ValueError("This pool does not record exact loop words for a controlled contrast.")
    preserved = choices.preserve(
        choices.select(history[-1]), stage="hairpin", except_neighborhood="loop"
    )
    # Retain all active constraints, including an existing preservation control.
    # Exact membership intersects them without combining independent axis ranges.
    preserved.update(
        parameters=current["query"]["parameters"],
        membership={
            "snapshot_digest": current["snapshot_digest"],
            "preparations": sorted(
                i
                for i, p in rows.items()
                if p["matches"] and (candidates is None or i in candidates)
            ),
        },
    )
    result = choices.query(preserved)
    for path in result["paths"]:
        path["matches"] = path["matches"] and path["values"].get("loop_word") != word
    if not any(p["matches"] for p in result["paths"]):
        raise NoLoopAlternative(
            "No different loop preserves these surroundings under the current filters "
            + (
                "among these candidates. Other preparations were not tested. "
                if candidates is not None
                else "in this recorded pool. "
            )
            + "No requirement was relaxed."
        )
    return result


def coordinate_changes(before: Record, after: Record) -> list[Record]:
    """Describe each changed canonical coordinate once across navigation operations."""
    changes, seen = [], set()
    for key in sorted(before.keys() | after.keys()):
        if before.get(key) == after.get(key):
            continue
        definition = parameter_definition(key)
        if definition.canonical_key in seen:
            continue
        seen.add(definition.canonical_key)
        changes.append(
            {
                "key": key,
                "label": definition.label,
                "before": before.get(key),
                "after": after.get(key),
                "unit": definition.unit,
                "stage": definition.stage,
            }
        )
    return changes


def describe_changes(changes: list[Record], *, limit: int = 3) -> str:
    visible = [
        c
        for c in changes
        if parameter_definition(c["key"]).design_role == "product"
        and parameter_definition(c["key"]).role != "derived"
    ]
    if visible:
        description = "; ".join(
            f"{c['label']}: {c['before'] if c['before'] is not None else 'not applicable'}"
            f" → {c['after'] if c['after'] is not None else 'not applicable'}"
            f"{' ' + c['unit'] if c['unit'] else ''}"
            for c in visible[:limit]
        )
        return description + (
            f"; +{len(visible) - limit} product changes" if len(visible) > limit else ""
        )
    if any(c["key"] == "background" for c in changes):
        return "Outside-loop scaffold differs."
    if changes:
        return "Construction details change; displayed product parameters agree."
    return "Displayed parameters agree; exact sequences can differ."


def describe_choice(values: Record) -> str:
    """Orient a first inspection using recorded molecular features."""
    parts = []
    if values.get("loop_word") is not None:
        parts.append(f"Loop {values['loop_word']}")
    if values.get("foldback_arm_bp") is not None:
        parts.append(f"{values['foldback_arm_bp']} bp loop-side extension")
    return " · ".join(parts)


def explain_choice(answer: Record, identity: str, *, reference: str | None = None) -> Record:
    if reference == identity:
        reference = None
    rows = {
        p["materialized_realization_id"]: p
        for p in answer["paths"]
        if p["materialized_realization_id"] in {identity, reference}
    }
    if identity not in rows or (reference is not None and reference not in rows):
        raise ValueError("Comparison must name recorded preparations.")
    changes = (
        coordinate_changes(rows[reference]["values"], rows[identity]["values"]) if reference else []
    )
    return {
        "materialized_realization_id": identity,
        "reference_identity": reference,
        "basis": "recorded_parameters",
        "coordinate_changes": changes,
        "description": (
            describe_changes(changes, limit=2)
            if reference
            else describe_choice(rows[identity]["values"])
        ),
    }
