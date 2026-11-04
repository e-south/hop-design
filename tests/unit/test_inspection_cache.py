"""Preview eviction removes owned files; browser exports keep a separate lifetime."""

import json

import pytest

from hop_design.commands.design.inspection_cache import PreviewCache


class Packet:
    json_bytes = json.dumps({"atlas": {"materialized_realization_id": "example"}}).encode()
    overview = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1008 280"/>'

    def inspection_summary(self, selection):
        return {"selection": selection}

    def write(self, path, *, print_pages):
        assert not print_pages
        path.mkdir()
        (path / "projection.svg").write_bytes(b"x" * 80)
        (path / "overview.svg").write_bytes(self.overview)


class Choices:
    def atlas(self, selection, **kwargs):
        return Packet()


def test_preview_cache_evicts_disk_and_memory_and_cleans_on_close(tmp_path):
    item_bytes = 80 + len(Packet.overview)
    cache = PreviewCache(tmp_path, entries=2, byte_limit=2 * item_bytes + 20)
    first = cache.get(Choices(), {"materialized_realization_id": "a"})
    first_file = tmp_path / first["drawing"].removeprefix("/files/")
    assert first_file.exists()
    for identity in ("b", "c", "d", "e"):
        cache.get(Choices(), {"materialized_realization_id": identity})
    assert not first_file.exists()
    assert cache.bytes == 2 * item_bytes
    assert len(list(cache.root.glob("*/projection.svg"))) == 2
    root = cache.root
    cache.close()
    assert cache.bytes == 0 and not root.exists()


def test_oversized_preview_is_not_retained_after_failure(tmp_path):
    cache = PreviewCache(tmp_path, byte_limit=60)
    with pytest.raises(ValueError, match="exceeds"):
        cache.get(Choices(), {"materialized_realization_id": "a"})
    assert cache.bytes == 0 and not list(cache.root.iterdir())
    cache.close()
