"""Producer checks hash the same complete source bytes without stat-based caching."""

import os

from hop_design.design.runtime import _source_fingerprints
from hop_design.serialization import sha256_digest


def reference(root):
    return {
        path.relative_to(root).as_posix(): sha256_digest(path.read_bytes())
        for path in sorted(root.rglob("*.py"))
    }


def test_fast_source_walk_matches_pathlib_scope_and_detects_preserved_stat_edit(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    source = nested / "source.py"
    source.write_bytes(b"x = 1\n")
    (tmp_path / "data.json").write_bytes(b"{}")
    (tmp_path / "__init__.py").write_bytes(b"")
    (tmp_path / "linked.py").symlink_to(source)
    (tmp_path / "ignored-directory-link").symlink_to(nested, target_is_directory=True)
    before = _source_fingerprints(tmp_path)
    assert before == reference(tmp_path)
    stat = source.stat()
    source.write_bytes(b"x = 2\n")
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    after = _source_fingerprints(tmp_path)
    assert after == reference(tmp_path)
    assert before != after
