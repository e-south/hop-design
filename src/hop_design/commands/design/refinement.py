"""CLI translations for molecular preservation and deliberate comparison membership."""

import json
from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction

from .common import emit, errors, load_choices, save_document, write_selection
from .presentation import OutputFormat, use_text


def register_refinement_commands(app: typer.Typer) -> None:
    @app.command("preserve")
    def preserve(
        directory: Path,
        reference: Annotated[Path, typer.Option(help="Saved exact reference selection.")],
        stage: Annotated[str, typer.Option(help="hairpin or endpoint")],
        except_neighborhood: Annotated[str, typer.Option(help="Neighborhood allowed to vary.")],
        output: Annotated[
            Path | None, typer.Option("--out", help="New refinement JSON file.")
        ] = None,
    ) -> None:
        """Hold a selected molecule's surroundings in a new query; no search starts."""
        with errors():
            query = load_choices(directory).preserve(
                reference,
                stage=stage,
                except_neighborhood=except_neighborhood,
            )
            write_selection(query, output, directory)

    @app.command("compare")
    def compare(
        directory: Path,
        request: Annotated[Path, typer.Option(help="Required members, stage and controls.")],
        query: Annotated[Path | None, typer.Option(help="Saved filters or preservation.")] = None,
        output: Annotated[
            Path | None, typer.Option("--out", help="New comparison JSON file.")
        ] = None,
        format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.AUTO,
    ) -> None:
        """Assess required sets within complete choices; no set is selected."""
        with errors():
            result = construction.load_design_choices(directory).compare(request, query=query)
            save_document(result, output, directory)
            if not use_text(format):
                emit(result)
                return
            count = len(result["sets"])
            typer.echo(f"{count} compatible {'set' if count == 1 else 'sets'}; none selected.")
            typer.echo(f"Comparison stage: {result['comparison_stage']}.")
            for member in result["members"]:
                words = f" (loop {member['loop_sequence']})" if "loop_sequence" in member else ""
                typer.echo(
                    f"  {member['name']}{words}: "
                    f"{len(member['option_labels'])} matching preparations."
                )
            for missing in result["missing_members"]:
                reason = (
                    "excluded by the active refinement"
                    if missing["reason"] == "excluded_by_query"
                    else "not observed among the evaluated preparations"
                )
                typer.echo(f"Missing {missing['name']}: {reason}.")
            coverage = result["group_coverage"]
            typer.echo(
                f"Examined {coverage['evaluated_assignments']} of "
                f"{coverage['possible_assignments']} possible member assignments in this pool."
            )
            if count:
                for selected in result["sets"][:5]:
                    typer.echo(f"  {selected['label']}: {', '.join(selected['members'])}")
                typer.echo("Choose a set and a named baseline with design select-set.")
            elif not result["missing_members"] and not coverage["unexamined_assignments"]:
                typer.echo(
                    "The examined members do not satisfy the shared comparison requirements."
                )
            if output is not None:
                typer.echo(f"Full comparison: {output}")

    @app.command("select-set")
    def select_set(
        directory: Path,
        comparison: Annotated[Path, typer.Option(help="Saved comparison assessment.")],
        set_label: Annotated[str, typer.Option(help="Explicit set from the assessment.")],
        baseline: Annotated[str, typer.Option(help="Named member to use as comparison baseline.")],
        output: Annotated[
            Path | None, typer.Option("--out", help="New set selection JSON file.")
        ] = None,
    ) -> None:
        """Select a required comparison for the ordinary preparation retrieval command."""
        with errors():
            selected = construction.load_design_choices(directory).select_set(
                comparison,
                set_label=set_label,
                baseline=baseline,
            )
            write_selection(selected, output, directory)

    @app.command("select-members")
    def select_members(
        directory: Path,
        members: Annotated[
            Path, typer.Option(help="JSON mapping required member names to their saved selections.")
        ],
        baseline: Annotated[str, typer.Option(help="Explicit required member used as baseline.")],
        output: Annotated[Path | None, typer.Option("--out")] = None,
    ) -> None:
        """Verify one selected preparation for every required stem, including shared controls."""
        with errors():
            roster = json.loads(members.read_bytes())
            if not isinstance(roster, dict):
                raise ValueError("Membership must map required stem names to saved selections.")
            selected = construction.load_design_choices(directory).select_members(
                roster,
                baseline=baseline,
            )
            write_selection(selected, output, directory)
