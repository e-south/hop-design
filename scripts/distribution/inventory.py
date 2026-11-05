"""Check archive membership and packaged bytes without running scientific cases."""

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

# Public content promised by the existing distribution gate.
REQUIRED_SOURCE_PATHS = (
    "LICENSE",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "ARCHITECTURE.md",
    "DESIGN.md",
    "RELIABILITY.md",
    "assets/hop-design-banner.svg",
    "assets/examples/basal-junction.svg",
    "assets/examples/foldback-junction.svg",
    "docs/index.md",
    "docs/guides/install.md",
    "docs/guides/quickstart.md",
    "examples/author_linear_source_method.py",
    "examples/compile_payload_records.py",
    "examples/compile_construction.py",
    "examples/complete-construction/README.md",
    "examples/complete-construction/product-request.json",
    "examples/complete-construction/run.py",
    "examples/complete-construction/family.py",
    "examples/scaffold-options/run.py",
    "examples/scaffold-options/insert.json",
    "examples/scaffold-options/hairpin.json",
    "examples/scaffold-options/comparison.json",
    "examples/scaffold-discovery/request.json",
    "examples/scaffold-discovery/run.py",
    "examples/scaffold-discovery/terminal-form.json",
    "examples/scaffold-discovery/terminal_forms.py",
    "examples/scaffold-comparison/run.py",
    "examples/scaffold-comparison/controlled_panel.py",
    "examples/scaffold-comparison/crossed.json",
    "examples/scaffold-comparison/methods.json",
    "examples/scaffold-comparison/hairpin.json",
    "examples/scaffold-comparison/grouped.json",
    "examples/scaffold-comparison/loop-sequences.json",
    "examples/molecular-editing/README.md",
    "examples/molecular-editing/request.json",
    "examples/molecular-editing/sequence-family.json",
    "examples/molecular-editing/run.py",
    "examples/molecular-editing/conditional.py",
    "examples/molecular-editing/parameters.py",
    "examples/molecular-editing/envelope.py",
    "examples/molecular-editing/construction-envelope.json",
    "docs/guides/explore-conditional-variants.md",
    "docs/guides/edit-folded-sequences.md",
    "examples/construction-composed-pcr.yaml",
    "examples/compile_linear_source_method.py",
    "examples/construction-exact-design.yaml",
    "examples/construction-exact.yaml",
    "examples/construction-infeasible.yaml",
    "examples/construction-expanded-domain.yaml",
    "examples/discover_basal_candidates.py",
    "examples/fixed-site-three-base-context.yaml",
    "examples/loxp-spacer.yaml",
    "examples/loxp-spacer-base-classes.yaml",
    "examples/basal-junction/README.md",
    "examples/basal-junction/request.yaml",
    "examples/basal-junction/search.py",
    "examples/foldback-local-partition.yaml",
    "examples/foldback-sequence-space.yaml",
    "examples/basal-sequence-space.yaml",
    "examples/generic-symbolic.yaml",
    "examples/linear-source-matched-design.yaml",
    "examples/linear-source-method.json",
    "examples/render_component_views.py",
    "examples/verify_design_method_handoff.py",
)


def require_archives(source: Path, wheel: Path, sdist: Path) -> None:
    expected = {
        str(path.relative_to(source / "src")): path.read_bytes()
        for path in (source / "src/hop_design").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        if len(roots) != 1:
            raise ValueError("Expected one source distribution root")
        paths = {
            str(PurePosixPath(member.name).relative_to(next(iter(roots))))
            for member in members
            if member.isfile()
        }
        forbidden = {".agents", ".github", "scripts", "tests"}
        if any(forbidden.intersection(PurePosixPath(member.name).parts[1:]) for member in members):
            raise ValueError("Repository-only content in source distribution")
        missing = set(REQUIRED_SOURCE_PATHS) - paths
        if missing:
            raise ValueError(f"Missing source distribution content: {sorted(missing)}")
        root = next(iter(roots))
        promised = {path: (source / path).read_bytes() for path in REQUIRED_SOURCE_PATHS}
        promised.update({f"src/{path}": data for path, data in expected.items()})
        for name, data in promised.items():
            if name not in paths:
                raise ValueError(f"Missing source distribution content: {name}")
            content = archive.extractfile(f"{root}/{name}")
            if content is None or content.read() != data:
                raise ValueError(f"Changed source distribution bytes: {name}")
    with zipfile.ZipFile(wheel) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.startswith("hop_design/") and not name.endswith("/")
        ]
        if not expected or len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Wheel package membership differs from source")
        for name, data in expected.items():
            if archive.read(name) != data:
                raise ValueError(f"Wheel package bytes differ: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    args = parser.parse_args()
    require_archives(args.source, args.wheel, args.sdist)
    print("Archive inventory and package bytes: passed")
