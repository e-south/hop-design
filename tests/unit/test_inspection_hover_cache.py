"""Route browsing cannot evict the teaching working set by entry count alone."""

from hop_design.commands.design.inspection_hover import HoverCache


def test_route_churn_retains_teaching_artwork_within_the_shared_byte_budget(tmp_path):
    cache = HoverCache(tmp_path, entries=2, byte_limit=12)
    calls = []

    def build(path):
        calls.append(path.name)
        (path / "drawing.svg").write_bytes(b"svg")
        return {"identity": path.name}

    try:
        first = cache._retain("hairpin-a", build)
        cache._retain("hairpin-b", build)
        for identity in ("route-a", "route-b", "route-c"):
            cache._retain(identity, build, scenes=True)
        assert cache._retain("hairpin-a", build) == first
        assert calls.count("hairpin-a") == 1
        assert not (cache.root / "route-a").exists()
        assert len(list(cache.root.iterdir())) == 4
        assert cache.bytes == 12
        # The unchanged byte ceiling applies across both working sets.
        cache._retain("larger", _large_drawing)
        assert cache.bytes <= 12
        assert not (cache.root / "hairpin-b").exists()
        root = cache.root
    finally:
        cache.close()
    assert not root.exists() and cache.bytes == 0


def _large_drawing(path):
    (path / "drawing.svg").write_bytes(b"longer-svg")
    return {"identity": path.name}
