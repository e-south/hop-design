"""Installation qualification rejects source leakage and reports failed stages."""

import json
import runpy
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def helper(name):
    return runpy.run_path(str(ROOT / "scripts/distribution" / name))


def test_import_must_be_inside_the_isolated_environment(tmp_path):
    require = helper("probe.py")["require_installed"]
    prefix = tmp_path / "venv"
    module = prefix / "lib/site-packages/hop_design/__init__.py"
    module.parent.mkdir(parents=True)
    module.touch()
    require(prefix, prefix, module)
    with pytest.raises(ValueError, match="outside"):
        require(prefix, prefix, ROOT / "src/hop_design/__init__.py")
    with pytest.raises(ValueError, match="environment"):
        require(prefix, tmp_path / "other", module)


def test_missing_browser_asset_is_an_installation_failure(tmp_path):
    check = helper("probe.py")["require_assets"]
    with pytest.raises(ValueError, match="Missing packaged asset"):
        check(tmp_path)


def test_handoff_comparison_checks_content_and_membership(tmp_path):
    helpers = runpy.run_path(str(ROOT / "scripts/design-discovery-smoke.py"))
    compare = helpers["require_same_handoff"]
    left, right = tmp_path / "left", tmp_path / "right"
    left.mkdir()
    right.mkdir()
    with pytest.raises(ValueError, match="handoff"):
        compare(left, right)
    for path in (left, right):
        (path / "oligos.csv").write_text("sequence,chemistry\nACGT,phosphate\n")
    compare(left, right)
    (right / "oligos.csv").write_text("sequence,chemistry\nACGT,hydroxyl\n")
    with pytest.raises(ValueError, match="handoff"):
        compare(left, right)
    (right / "oligos.csv").write_bytes((left / "oligos.csv").read_bytes())
    (right / "unexpected.txt").touch()
    with pytest.raises(ValueError, match="handoff"):
        compare(left, right)


def test_stage_records_timings_and_propagates_subprocess_failure(tmp_path):
    runner = helper("smoke.py")["Stages"](tmp_path)
    runner.run("success", [sys.executable, "-c", "print('ready')"], cwd=tmp_path)
    with pytest.raises(RuntimeError, match="broken"):
        runner.run("broken", [sys.executable, "-c", "raise SystemExit(7)"], cwd=tmp_path)
    rows = json.loads((tmp_path / "stages.json").read_text())
    assert [row["status"] for row in rows] == ["passed", "failed"]
    assert rows[-1]["returncode"] == 7
    assert all(row["seconds"] >= 0 for row in rows)
    assert (tmp_path / rows[0]["log"]).read_text() == "ready\n"


def test_stage_timeout_is_recorded_and_not_reported_as_success(tmp_path):
    runner = helper("smoke.py")["Stages"](tmp_path)
    with pytest.raises(RuntimeError, match="timed out"):
        runner.run(
            "timeout",
            [sys.executable, "-c", "import time; time.sleep(10)"],
            cwd=tmp_path,
            timeout=0.05,
        )
    assert json.loads((tmp_path / "stages.json").read_text())[-1]["status"] == "timeout"


def test_archive_inventory_rejects_omitted_or_changed_package_files(tmp_path):
    inventory = helper("inventory.py")
    source = tmp_path / "source"
    package = source / "src/hop_design"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n")
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    public = source / "public.txt"
    public.write_text("Public documentation\n")
    with tarfile.open(sdist, "w:gz") as archive:
        for path in inventory["REQUIRED_SOURCE_PATHS"]:
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(public.read_bytes())
            archive.add(public, arcname=f"package/{path}")
        archive.add(package / "__init__.py", arcname="package/src/hop_design/__init__.py")
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("hop_design/__init__.py", "VALUE = 1\n")
    inventory["require_archives"](source, wheel, sdist)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("hop_design/__init__.py", "VALUE = 2\n")
    with pytest.raises(ValueError, match="package bytes"):
        inventory["require_archives"](source, wheel, sdist)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("metadata.txt", "empty package")
    with pytest.raises(ValueError, match="package membership"):
        inventory["require_archives"](source, wheel, sdist)
    (source / "README.md").write_text("Changed after build\n")
    with pytest.raises(ValueError, match="source distribution bytes"):
        inventory["require_archives"](source, wheel, sdist)


@pytest.mark.parametrize("bad_name", ["package/tests/private.py", "package/README.md.fake"])
def test_archive_inventory_checks_exact_sdist_membership(tmp_path, bad_name):
    inventory = helper("inventory.py")
    sdist = tmp_path / "package.tar.gz"
    payload = tmp_path / "payload"
    payload.write_text("data")
    with tarfile.open(sdist, "w:gz") as archive:
        archive.add(payload, arcname=bad_name)
    with pytest.raises(ValueError, match="source distribution"):
        inventory["require_archives"](tmp_path, tmp_path / "unused.whl", sdist)
