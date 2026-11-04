"""Compressed captured authorities cannot introduce unsafe paths or unbounded expansion."""

import io
from zipfile import ZipFile, ZipInfo

import pytest

from hop_design.design.construction.editions.materials import ArchivedMaterials, archive_materials


@pytest.mark.parametrize("name", ["../outside", "/absolute", "nested/../../outside", "a\\b"])
def test_archive_rejects_unsafe_paths(name):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        info = ZipInfo(name)
        info.external_attr = 0o100600 << 16
        archive.writestr(info, b"x")
    with pytest.raises(ValueError, match="paths"):
        ArchivedMaterials(buffer.getvalue())


def test_archive_rejects_symbolic_links():
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        info = ZipInfo("link")
        info.external_attr = 0o120777 << 16
        archive.writestr(info, b"../outside")
    with pytest.raises(ValueError, match="ordinary files"):
        ArchivedMaterials(buffer.getvalue())


def test_archive_limits_expansion_before_reading_members(tmp_path, monkeypatch):
    from hop_design.design.construction.editions import materials

    root = tmp_path / "materials"
    root.mkdir()
    (root / "record.json").write_bytes(b"A" * 100)
    archive_materials(root, tmp_path / "materials.zip")
    monkeypatch.setattr(materials, "MAX_MEMBER_BYTES", 10)
    with pytest.raises(ValueError, match="authority limit"):
        ArchivedMaterials((tmp_path / "materials.zip").read_bytes())


def test_archive_is_deterministic_and_lossless(tmp_path):
    root = tmp_path / "materials"
    root.mkdir()
    (root / "oligos.csv").write_bytes(b"name,sequence\nsource,ACGT\n")
    archive_materials(root, tmp_path / "one.zip")
    archive_materials(root, tmp_path / "two.zip")
    assert (tmp_path / "one.zip").read_bytes() == (tmp_path / "two.zip").read_bytes()
    assert dict(ArchivedMaterials((tmp_path / "one.zip").read_bytes())) == {
        "oligos.csv": (root / "oligos.csv").read_bytes()
    }
