"""Explicit packaged asset routes for each local interaction surface."""

from importlib.resources import files

_VARIANT_MODULES = frozenset(
    [
        "inspection",
        "comparison",
        "navigation",
        "query",
        "selection",
        "common",
        "continuity",
        "motion",
        "strand_curve",
        "atlas_view",
        "envelope",
        "camera_geometry",
        "grouped_navigation",
        "local_choices",
        "local_choice_model",
        "camera",
        "inspection_labels",
        "choice_space",
        "choice_space_model",
        "choice_space_axes",
        "choice_space_brush",
        "choice_space_coverage",
        "parameter_key",
        "primer_boundary",
        "choice_space_local",
        "choice_space_plot",
        "envelope_browser",
        "envelope_model",
        "envelope_fields",
    ]
)
_SURVEY_MODULES = frozenset(
    {"plot", "model", "atlas", "atlas_position", "parameters", "selected_views", "teaching_links"}
)


def asset_response(mode: str, route: str, token: str) -> tuple[bytes, str] | None:
    folder = {
        "variant": "variant_explorer",
        "survey": "survey_explorer",
        "design": "design_explorer",
        "editor": "molecular_editor",
    }[mode]
    name = "index.html" if route == "/" else route.removeprefix("/")
    permitted = {"index.html", "editor.js", "editor.css"}
    if mode == "design":
        permitted |= {
            "landscape.js",
            "member_choices.js",
            "artifacts.js",
            "local_choices.js",
            "linked_focus.js",
            "hover_preview.js",
            "map_camera.js",
            "neighbors.js",
            "inspection_overlay.js",
            "persistent_scene.js",
            "cohort_state.js",
            "pending_render.js",
            "figure_layout.js",
            "map_raster.js",
            "map_index.js",
            "indexed_map.js",
            "panel_status.js",
            "inspection_loading.js",
            "molecular_colors.js",
            "color_controls.js",
            "inspection_facts.js",
            "comparison_features.js",
            "route_scenes.js",
            "route_scene_work.js",
            "inspector_resize.js",
            "discovery.js",
        }
        if name in {f"{n}.js" for n in _SURVEY_MODULES}:
            return files("hop_design").joinpath(
                f"assets/survey_explorer/{name}"
            ).read_bytes(), "text/javascript; charset=utf-8"
        if name in {"camera_geometry.js", "grouped_navigation.js"}:
            return files("hop_design").joinpath(
                f"assets/variant_explorer/{name}"
            ).read_bytes(), "text/javascript; charset=utf-8"
    if mode in {"variant", "survey"} and route == "/teaching_links.js":
        return files("hop_design").joinpath(
            "assets/survey_explorer/teaching_links.js"
        ).read_bytes(), "text/javascript; charset=utf-8"
    if mode == "variant":
        permitted |= {f"{n}.js" for n in _VARIANT_MODULES}
    elif mode == "survey":
        permitted |= {f"{n}.js" for n in _SURVEY_MODULES}
        if route in {"/camera_geometry.js", "/grouped_navigation.js"}:
            return files("hop_design").joinpath(
                f"assets/variant_explorer/{name}"
            ).read_bytes(), "text/javascript; charset=utf-8"
    if route != "/" and (not route.startswith("/") or name == "index.html"):
        return None
    if name not in permitted:
        return None
    content = files("hop_design").joinpath(f"assets/{folder}/{name}").read_bytes()
    if route == "/":
        content = content.replace(b"__SESSION_TOKEN__", token.encode())
    suffix = name.rsplit(".", 1)[-1]
    return content, {"html": "text/html", "js": "text/javascript", "css": "text/css"}[
        suffix
    ] + "; charset=utf-8"
