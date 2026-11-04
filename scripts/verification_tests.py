"""Presentation checks: verified molecular records through projections and drawings.

This is an explicit responsibility map, not a filename-based impact predictor.
Search, materialization and independent bundle admission belong to source checks.
"""

from pathlib import Path

PRESENTATION = (
    "tests/unit/test_atlas*.py",
    "tests/unit/test_print*.py",
    "tests/unit/test_molecular*.py",
    "tests/unit/test_recognition_ribbon.py",
    "tests/unit/test_recognition_labels.py",
    "tests/unit/test_teaching_svg_portability.py",
    "tests/unit/test_survey_plot*.py",
    "tests/unit/test_survey_figure_layout.py",
    "tests/unit/test_survey_trace_projection.py",
    "tests/unit/test_inspection_cache.py",
    "tests/unit/test_inspection_worker.py",
    # Background-job transport/lifecycle; real discovery remains source scope.
    "tests/unit/test_inspection_discovery.py",
    "tests/unit/test_inspection_discovery_adapter.py",
    "tests/unit/test_inspection_discovery_adoption.py",
    "tests/unit/test_inspection_discovery_http.py",
    "tests/unit/test_inspection_plots.py",
    "tests/unit/test_inspection_facts.py",
    "tests/unit/test_parameter_boundary_rendering.py",
    "tests/unit/test_parameter_display_labels.py",
    "tests/unit/test_choice_presentation.py",
    "tests/contract/test_view_contracts.py",
    "tests/contract/test_basal_source_view.py",
    "tests/contract/test_construction_projection_authority_hardening.py",
    "tests/integration/test_atlas*.py",
    "tests/integration/test_molecular_atlas.py",
    "tests/integration/test_molecular_preview.py",
    "tests/integration/test_compact_preview_context.py",
    "tests/integration/test_molecular_drawing_primitives.py",
    "tests/integration/test_molecular_editor_http.py",
    "tests/integration/test_design_inspection_http.py",
    "tests/integration/test_lazy_route_inspection.py",
    "tests/integration/test_inspection_geometry.py",
    "tests/integration/test_parameter_teaching.py",
    "tests/integration/test_primer_boundary_projection.py",
    "tests/integration/test_scaffold_inspection.py",
    "tests/integration/test_construction_end_inspection.py",
    "tests/integration/test_survey_projection_inspection.py",
    "tests/integration/test_survey_atlas_comparison.py",
    "tests/integration/test_survey_figure.py",
    "tests/integration/test_figure_display_projection.py",
    "tests/integration/test_space_figures.py",
)

# Edition capture, admission and relocation exercise the source lifecycle even
# though their filename also matches the atlas drawing pattern above.
SOURCE_ONLY = frozenset({"tests/integration/test_atlas_edition.py"})


def presentation_tests(root: Path) -> list[str]:
    selected = set()
    for pattern in PRESENTATION:
        matches = [p for p in root.glob(pattern) if p.is_file()]
        if not matches:
            raise ValueError(f"Presentation verification pattern matched no tests: {pattern}")
        selected.update(str(p.relative_to(root)) for p in matches)
    return sorted(selected - SOURCE_ONLY)


if __name__ == "__main__":
    print("\n".join(presentation_tests(Path.cwd())))
