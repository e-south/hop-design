"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/__init__.py

Registers construction navigation commands on one specialist CLI group.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import typer

from .comparison import construction_compare_command
from .routes import construction_list_command
from .selection import construction_inspect_command, construction_select_command
from .summary import construction_summary_command

construction_app = typer.Typer(
    help="Inspect and select exact routes from a verified construction bundle.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
construction_app.command("summary")(construction_summary_command)
construction_app.command("list")(construction_list_command)
construction_app.command("inspect")(construction_inspect_command)
construction_app.command("select")(construction_select_command)
construction_app.command("compare")(construction_compare_command)

__all__ = ["construction_app"]
