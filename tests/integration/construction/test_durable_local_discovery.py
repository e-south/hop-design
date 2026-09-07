"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/construction/test_durable_local_discovery.py

Tests portable, bounded local-discovery execution and producer-bound resumption.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import pytest
import yaml

from hop_design.construction import discover_local_neighborhood, discover_local_neighborhoods
from hop_design.serialization import canonical_json_bytes, sha256_digest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sources(directory: Path) -> tuple[Path, ...]:
    source = yaml.safe_load((REPO_ROOT / "examples/foldback-local-partition.yaml").read_text())
    paths = []
    for index in range(2):
        source["search"]["sequence_partition"]["part_index"] = index
        target = directory / f"request-{index}.json"
        target.write_text(json.dumps(source), encoding="utf-8")
        paths.append(target)
    return tuple(paths)


def test_local_discovery_resumes_without_replacing_completed_results(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    expected = tuple(discover_local_neighborhood(source).json_bytes for source in sources)
    destination = tmp_path / "discovery"

    partial = discover_local_neighborhoods(sources, destination, max_new_requests=1, batch_size=1)
    assert partial.planned_requests == 2
    assert partial.completed_requests == 1
    assert not partial.finished
    assert tuple(result.json_bytes for result in partial.iter_results()) == expected[:1]
    saved = {
        path.relative_to(destination): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in destination.rglob("*")
        if path.is_file()
    }

    resumed = discover_local_neighborhoods(sources, destination, resume=True, batch_size=2)
    assert resumed.finished
    assert resumed.completed_requests == 2
    assert tuple(result.json_bytes for result in resumed.iter_results()) == expected
    for relative, (content, modified_at) in saved.items():
        assert (destination / relative).read_bytes() == content
        assert (destination / relative).stat().st_mtime_ns == modified_at


def test_receipt_keeps_its_completed_prefix_when_execution_advances(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    partial = discover_local_neighborhoods(sources, output, max_new_requests=1)
    before = tuple(result.json_bytes for result in partial.iter_results())
    discover_local_neighborhoods(sources, output, resume=True)
    assert tuple(result.json_bytes for result in partial.iter_results()) == before


def test_unpublished_staging_is_not_an_authority(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    discover_local_neighborhoods(sources, output, max_new_requests=1)
    abandoned = output / "batches" / ".pending-interrupted"
    abandoned.mkdir()
    (abandoned / "results.jsonl.gz").write_bytes(b"incomplete")
    resumed = discover_local_neighborhoods(sources, output, resume=True)
    assert resumed.finished
    assert len(tuple(resumed.iter_results())) == 2
    assert (abandoned / "results.jsonl.gz").read_bytes() == b"incomplete"


@pytest.mark.parametrize("field", ["producer", "request", "schema", "numeric_coercion"])
def test_resume_rejects_plan_changes(tmp_path: Path, field: str) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    discover_local_neighborhoods(sources, output, max_new_requests=1)
    path = output / "plan.json"
    plan = json.loads(path.read_bytes())
    if field == "producer":
        plan["producer"]["package_content"] = "sha256:" + "0" * 64
    elif field == "request":
        plan["requests"][0]["search"]["max_search_nodes"] = 1
    elif field == "numeric_coercion":
        plan["requests"][0]["search"]["max_search_nodes"] = 100.0
    else:
        plan["schema"] = "hop.local-neighborhood-execution/v2"
    path.write_bytes(canonical_json_bytes(plan))
    with pytest.raises(ValueError, match=r"plan.*producer"):
        discover_local_neighborhoods(sources, output, resume=True)


@pytest.mark.parametrize("target", ["plan.json", "batches", "batches/000000/results.jsonl.gz"])
def test_resume_rejects_symlinks(tmp_path: Path, target: str) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    discover_local_neighborhoods(sources, output, max_new_requests=1)
    target_path = output / target
    saved = tmp_path / "saved"
    target_path.rename(saved)
    target_path.symlink_to(saved, target_is_directory=saved.is_dir())
    with pytest.raises(ValueError, match="symlink"):
        discover_local_neighborhoods(sources, output, resume=True)


def test_resealed_result_still_requires_molecular_replay(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    discover_local_neighborhoods(sources, output, max_new_requests=1)
    batch = output / "batches" / "000000"
    result_file = batch / "results.jsonl.gz"
    result = json.loads(gzip.decompress(result_file.read_bytes()))
    result["result_id"] = "sha256:" + "0" * 64
    content = canonical_json_bytes(result)
    compressed = gzip.compress(content, mtime=0)
    result_file.write_bytes(compressed)
    inventory_file = batch / "inventory.json"
    inventory = json.loads(inventory_file.read_bytes())
    inventory["compressed_digest"] = sha256_digest(compressed)
    inventory["result_digests"] = [sha256_digest(content)]
    inventory_file.write_bytes(canonical_json_bytes(inventory))
    with pytest.raises(ValueError, match=r"result_id|result identity|digest"):
        discover_local_neighborhoods(sources, output, resume=True)


def test_finished_collection_preserves_truncated_search_status(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    source = json.loads(sources[0].read_bytes())
    source["search"]["max_search_nodes"] = 1
    sources[0].write_bytes(canonical_json_bytes(source))
    receipt = discover_local_neighborhoods(sources, tmp_path / "execution")
    assert receipt.finished
    assert next(receipt.iter_results()).completion == "truncated"


def test_completed_record_rejects_missing_batch(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    discover_local_neighborhoods(sources, output, batch_size=1)
    shutil.move(output / "batches" / "000001", tmp_path / "removed-batch")
    with pytest.raises(ValueError, match="completion record"):
        discover_local_neighborhoods(sources, output, resume=True)


@pytest.mark.parametrize(
    "corruption", ["compressed", "order", "extra_file", "extra_result", "duplicate_key", "request"]
)
def test_resume_rejects_invalid_batch_before_publishing(tmp_path: Path, corruption: str) -> None:
    sources = _sources(tmp_path)
    output = tmp_path / "execution"
    discover_local_neighborhoods(sources, output, max_new_requests=1)
    batch = output / "batches" / "000000"
    result_file = batch / "results.jsonl.gz"
    if corruption == "compressed":
        result_file.write_bytes(b"invalid gzip")
    elif corruption == "order":
        batch.rename(batch.with_name("000001"))
    elif corruption == "extra_file":
        (batch / "extra.json").write_text("{}")
    else:
        raw = gzip.decompress(result_file.read_bytes())
        if corruption == "extra_result":
            content = raw + raw
        elif corruption == "duplicate_key":
            content = b'{"schema":"duplicate",' + raw[1:]
        else:
            mapping = json.loads(raw)
            mapping["neighborhood"]["request"]["search"]["max_search_nodes"] = 1
            content = canonical_json_bytes(mapping)
        compressed = gzip.compress(content, mtime=0)
        result_file.write_bytes(compressed)
        inventory_file = batch / "inventory.json"
        inventory = json.loads(inventory_file.read_bytes())
        inventory["compressed_digest"] = sha256_digest(compressed)
        inventory["result_digests"] = [
            sha256_digest(raw if corruption == "extra_result" else content)
        ]
        inventory_file.write_bytes(canonical_json_bytes(inventory))
    with pytest.raises(ValueError):
        discover_local_neighborhoods(sources, output, resume=True)
    assert not (output / "complete.json").exists()


@pytest.mark.parametrize(
    "options",
    [
        {"batch_size": 0},
        {"batch_size": 257},
        {"batch_size": True},
        {"max_new_requests": 0},
        {"resume": 1},
    ],
)
def test_execution_controls_fail_before_writing(tmp_path: Path, options: dict) -> None:
    output = tmp_path / "execution"
    with pytest.raises(ValueError):
        discover_local_neighborhoods(_sources(tmp_path), output, **options)
    assert not output.exists()


def test_batching_and_destination_do_not_change_result_bytes(tmp_path: Path) -> None:
    sources = _sources(tmp_path)
    first = discover_local_neighborhoods(sources, tmp_path / "one", batch_size=1)
    second = discover_local_neighborhoods(sources, tmp_path / "two", batch_size=2)
    assert tuple(item.json_bytes for item in first.iter_results()) == tuple(
        item.json_bytes for item in second.iter_results()
    )
    with pytest.raises(FileExistsError):
        discover_local_neighborhoods(sources, tmp_path / "one")


def test_empty_collection_and_bare_path_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ordered collection"):
        discover_local_neighborhoods([], tmp_path / "empty")
    with pytest.raises(ValueError, match="ordered collection"):
        discover_local_neighborhoods("request.json", tmp_path / "bare")
