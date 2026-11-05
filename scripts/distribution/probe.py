"""Probe the installed artifact without adding pytest to its environment."""

import argparse
import json
import runpy
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


def require_installed(expected: Path, actual: Path, module: Path) -> None:
    if actual.resolve() != expected.resolve():
        raise ValueError("Unexpected Python environment")
    if not module.resolve().is_relative_to(expected.resolve()):
        raise ValueError("HOP import is outside the isolated environment")


def require_assets(package: Path) -> None:
    required = {
        "molecular_editor": ("index.html", "editor.js", "editor.css"),
        "variant_explorer": (
            "index.html",
            "editor.js",
            "editor.css",
            "choice_space_model.js",
            "choice_space_brush.js",
            "choice_space_axes.js",
            "choice_space_coverage.js",
            "choice_space_local.js",
            "parameter_key.js",
            "envelope_browser.js",
            "envelope_model.js",
            "envelope_fields.js",
        ),
        "survey_explorer": (
            "index.html",
            "editor.js",
            "editor.css",
            "model.js",
            "plot.js",
            "atlas.js",
        ),
    }
    for directory, names in required.items():
        for name in names:
            path = package / "assets" / directory / name
            if not path.is_file() or not path.stat().st_size:
                raise ValueError(f"Missing packaged asset: {directory}/{name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--case", required=True, type=Path)
    args = parser.parse_args()
    import hop_design
    from hop_design import construction

    require_installed(args.prefix, Path(sys.prefix), Path(hop_design.__file__))
    require_assets(Path(hop_design.__file__).parent)
    symbolic = hop_design.compile(sequence="NRY", design_id="installation-check")
    if not symbolic.bundle.manifest_digest:
        raise ValueError("Installed symbolic compilation has no identity")
    args.out.mkdir()
    case = runpy.run_path(str(args.case))
    # Preserve the existing example's finite budget; early evaluations can reject.
    result = case["run"](args.out, max_evaluations=64)
    choices = construction.load_design_choices(args.out / "designs")
    selection = args.out / "selection.json"
    selection.write_text(json.dumps(result["selection"]))
    cli = args.prefix / "bin/hop-design"
    installed_version = subprocess.check_output([str(cli), "--version"], text=True).strip()
    if installed_version != f"hop-design {version('hop-design')}":
        raise ValueError("CLI version differs from the installed distribution")
    subprocess.run(
        [
            str(cli),
            "design",
            "retrieve",
            str(args.out / "designs"),
            "--selection",
            str(selection),
            "--out",
            str(args.out / "cli-materials"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    case["require_same_handoff"](args.out / "preparation", args.out / "cli-materials")
    figure = choices.figure(selection=result["selection"]).write(args.out / "figure")
    if not (figure / "figure.pdf").read_bytes().startswith(b"%PDF"):
        raise ValueError("Installed renderer did not produce a PDF")
    if "<svg" not in (figure / "figure.svg").read_text():
        raise ValueError("Installed renderer did not produce an SVG")
    print(
        json.dumps(
            {
                "status": "passed",
                "installed_version": installed_version,
                "package_location": str(Path(hop_design.__file__).resolve()),
                "case": result,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
