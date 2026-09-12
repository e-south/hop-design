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

from .artifacts import (
    basal_panel_command,
    discover_batch_command,
    discover_construction_partition_command,
    discover_local_command,
    discover_partition_command,
    local_choices_command,
    project_command,
    verify_local_command,
    verify_partition_command,
)
from .comparison import construction_compare_command
from .compile import compile_local_design_command, compile_selected_command, verify_complete_command
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
construction_app.command("discover-local")(discover_local_command)
construction_app.command("verify-local")(verify_local_command)
construction_app.command("discover-batch")(discover_batch_command)
construction_app.command("discover-partition")(discover_partition_command)
construction_app.command("discover-construction-partition")(discover_construction_partition_command)
construction_app.command("verify-partition")(verify_partition_command)
construction_app.command("project")(project_command)
construction_app.command("local-choices")(local_choices_command)
construction_app.command("basal-panel")(basal_panel_command)
construction_app.command("compile-local-design")(compile_local_design_command)
construction_app.command("compile-selected")(compile_selected_command)
construction_app.command("verify-complete")(verify_complete_command)

__all__ = ["construction_app"]
