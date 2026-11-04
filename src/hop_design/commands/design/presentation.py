"""Terminal formatting for the same answer returned by the public choice object."""

import shlex
import sys
from enum import StrEnum
from pathlib import Path

import typer

from hop_design import construction

from .common import emit


class OutputFormat(StrEnum):
    AUTO = "auto"
    TEXT = "text"
    JSON = "json"


def use_text(format: OutputFormat) -> bool:
    return format == OutputFormat.TEXT or (format == OutputFormat.AUTO and sys.stdout.isatty())


def emit_choices(
    choices: construction.DesignChoices | construction.AtlasEdition,
    directory: Path,
    format: OutputFormat,
    query: Path | None = None,
) -> None:
    if not use_text(format):
        emit(choices.query(query))
        return
    answer = choices.explain(query)
    typer.echo(answer["headline"])
    if "required_members" in answer:
        for member in answer["members"]:
            typer.echo(
                f"  {member['name']}: {member['stem_arm']} — "
                f"{member['complete_preparations']} complete preparations."
            )
        typer.echo("Inspect one stem's choices with --member NAME.")
        if "select_members" in answer["actions"]:
            typer.echo("Select the required membership with design select-members.")
        else:
            typer.echo("Complete preparations are still missing; no family can be selected yet.")
        if "continue_search" in answer["actions"]:
            remaining = answer["max_total_evaluations"] - answer["reserved_evaluations"]
            typer.echo(f"Up to {remaining} further evaluations remain within the family bound.")
        elif answer["missing_members"]:
            typer.echo("Inspect member outcomes before explicitly revising the family request.")
        typer.echo(
            "Shared flank and material requirements are checked at selection; "
            "no pooled processing is assumed."
        )
        return
    if answer["choices"]:
        typer.echo(f"Distinct endpoint molecules: {answer['matching_products']['endpoint']}.")
        typer.echo("Available preparations (up to five shown; none selected):")
        for choice in answer["choices"]:
            values = choice["values"]
            facts = [
                f"{label} {values[key]}{unit}"
                for key, label, unit in (
                    ("loop_word", "loop", ""),
                    ("loop_nt", "loop size", " nt"),
                    ("loop_side_paired_bp", "loop-side addition", " bp"),
                    ("left_end_word", "left end", ""),
                    ("right_end_word", "right end", ""),
                )
                if values.get(key) is not None
            ]
            typer.echo("  " + "; ".join(facts + list(choice["methods"])))
    typer.echo(f"Saved choices: {directory}")
    root = shlex.quote(str(directory))
    filtering = "" if query is None else f" --query {shlex.quote(str(query))}"
    if "select" in answer["actions"]:
        typer.echo(f"Inspect: hop-design design view {root} --out ./design-view")
        typer.echo(
            f"Sample: hop-design design sample {root}{filtering} --seed 1 --out ./selection.json"
        )
    if "refine_query" in answer["actions"]:
        typer.echo("Refine the filter to inspect other recorded choices; no search is run.")
    if "continue_search" in answer["actions"]:
        typer.echo(
            f"Search further: hop-design design continue {root} --evaluations 64 --format text"
        )
    if "revise_request" in answer["actions"]:
        typer.echo(
            "Continuing unchanged cannot resolve this exclusion. "
            "Revise the request or context explicitly."
        )
    if "inspect_permissions" in answer["actions"]:
        typer.echo(f"Inspect permissions: {directory / 'intent' / 'summary.json'}")
    typer.echo(
        f"Full records and coverage: hop-design design query {root}{filtering} --format json"
    )
