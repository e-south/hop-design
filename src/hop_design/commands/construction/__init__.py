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
from .atlas import atlas_command
from .comparison import construction_compare_command
from .comparisons import (
    assess_comparison_command,
    execute_comparison_command,
    preview_comparison_command,
    select_comparison_command,
)
from .compile import compile_local_design_command, compile_selected_command, verify_complete_command
from .continue_request import construction_continue_command
from .editor.command import edit_view_command
from .edits import (
    evaluate_edit_command,
    prepare_edit_command,
    preview_edit_command,
    select_edit_command,
)
from .envelopes import evaluate_envelope_command, parameter_values_command, revise_envelope_command
from .execute import construction_execute_command
from .families import (
    author_family_command,
    execute_family_command,
    prepare_family_command,
    reconcile_family_command,
    report_family_command,
    select_set_command,
)
from .matching import match_family_command
from .options import explore_command, option_sets_command, select_options_command
from .parameter_evaluation import evaluate_parameters_command
from .portrait import construction_portrait_command
from .prepare import construction_prepare_command
from .routes import construction_list_command
from .scaffolds import (
    discover_scaffolds_command,
    preview_scaffolds_command,
    select_scaffolds_command,
)
from .selection import construction_inspect_command, construction_select_command
from .sequence_families import (
    evaluate_sequence_family_command,
    preview_sequence_family_command,
    select_sequence_family_command,
)
from .summary import construction_summary_command
from .survey import survey_app
from .variant_comparisons import compare_variants_command, select_variant_comparison_command
from .variant_preview import preview_variant_command
from .variants import inspect_variant_command, select_variants_command, variants_command

construction_app = typer.Typer(
    help="Inspect and select exact routes from a verified construction bundle.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
construction_app.add_typer(survey_app, name="survey")
construction_app.command("prepare-family")(prepare_family_command)
construction_app.command("preview-sequence-family")(preview_sequence_family_command)
construction_app.command("evaluate-sequence-family")(evaluate_sequence_family_command)
construction_app.command("select-sequence-family")(select_sequence_family_command)
construction_app.command("prepare-edit")(prepare_edit_command)
construction_app.command("edit-view")(edit_view_command)
construction_app.command("evaluate-parameters")(evaluate_parameters_command)
construction_app.command("revise-envelope")(revise_envelope_command)
construction_app.command("evaluate-envelope")(evaluate_envelope_command)
construction_app.command("parameter-values")(parameter_values_command)
construction_app.command("preview-edit")(preview_edit_command)
construction_app.command("evaluate-edit")(evaluate_edit_command)
construction_app.command("select-edit")(select_edit_command)
construction_app.command("variants")(variants_command)
construction_app.command("inspect-variant")(inspect_variant_command)
construction_app.command("atlas")(atlas_command)
construction_app.command("preview-variant")(preview_variant_command)
construction_app.command("compare-variants")(compare_variants_command)
construction_app.command("select-variant-comparison")(select_variant_comparison_command)
construction_app.command("select-variants")(select_variants_command)
construction_app.command("preview-comparison")(preview_comparison_command)
construction_app.command("assess-comparison")(assess_comparison_command)
construction_app.command("execute-comparison")(execute_comparison_command)
construction_app.command("select-comparison")(select_comparison_command)
construction_app.command("preview-scaffolds")(preview_scaffolds_command)
construction_app.command("discover-scaffolds")(discover_scaffolds_command)
construction_app.command("select-scaffolds")(select_scaffolds_command)
construction_app.command("explore")(explore_command)
construction_app.command("option-sets")(option_sets_command)
construction_app.command("select-options")(select_options_command)
construction_app.command("author-family")(author_family_command)
construction_app.command("execute-family")(execute_family_command)
construction_app.command("match-family")(match_family_command)
construction_app.command("reconcile-family")(reconcile_family_command)
construction_app.command("select-set")(select_set_command)
construction_app.command("report-family")(report_family_command)
construction_app.command("summary")(construction_summary_command)
construction_app.command("prepare")(construction_prepare_command)
construction_app.command("execute")(construction_execute_command)
construction_app.command("continue")(construction_continue_command)
construction_app.command("list")(construction_list_command)
construction_app.command("inspect")(construction_inspect_command)
construction_app.command("portrait")(construction_portrait_command)
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
