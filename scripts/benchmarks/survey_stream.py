"""
--------------------------------------------------------------------------------
HOP Design
scripts/benchmarks/survey_stream.py

Compare checkpoint streaming with the former per-record address lookup.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import argparse
import hashlib
import json
import platform
import statistics
import tempfile
import time
from pathlib import Path

from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def repeated_lookup(index):
    """Preserve the previous reader as a measured reference, outside runtime code."""
    for target, step, count, exhausted in index._db.execute(
        "SELECT ordinal,step,witness_count,exhausted FROM steps ORDER BY ordinal,step"
    ):
        yield target, step, index.record(target, step=step), count, bool(exhausted)


def consume(rows):
    digest, count = hashlib.sha256(), 0
    for target, step, raw, witnesses, exhausted in rows:
        digest.update(raw)
        digest.update(f"{target},{step},{witnesses},{exhausted}".encode())
        count += 1
    return count, digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=20_000)
    args = parser.parse_args()
    if not 1 <= args.records <= 65_536:
        parser.error("records must be between 1 and 65536")
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    producer = {"package_content": "synthetic-storage-benchmark"}
    readers = {"repeated_lookup": repeated_lookup, "stream": lambda index: index.evaluations()}
    observations = {name: {"stream": [], "open_and_stream": []} for name in readers}
    selects, expected = {}, None
    with tempfile.TemporaryDirectory(prefix="hop-stream-measurement-") as directory:
        path = Path(directory) / "synthetic.sqlite"
        with (
            SurveyIndex.create(path, request=request, producer=producer, format_version=2) as index,
            index.evaluation(),
        ):
            for ordinal in range(args.records):
                index.append(
                    ordinal,
                    step=0,
                    record=(f"{ordinal:08d}" + "A" * 92).encode(),
                    witness_count=0,
                    exhausted=False,
                )
        for scope in ("stream", "open_and_stream"):
            for trial in range(3):
                order = tuple(readers) if trial % 2 == 0 else tuple(reversed(readers))
                for name in order:
                    started = time.perf_counter()
                    with SurveyIndex.open(
                        path, request=request, producer=producer, read_only=True
                    ) as index:
                        if scope == "stream":
                            started = time.perf_counter()
                        result = consume(readers[name](index))
                    observations[name][scope].append(time.perf_counter() - started)
                    if expected is None:
                        expected = result
                    if result != expected:
                        raise ValueError("Reader changed ordered addresses or exact record bytes")
        for name, reader in readers.items():
            with SurveyIndex.open(
                path, request=request, producer=producer, read_only=True
            ) as index:
                statements = []
                index._db.set_trace_callback(statements.append)
                consume(reader(index))
                selects[name] = sum(sql.startswith("SELECT") for sql in statements)
    print(
        json.dumps(
            {
                "scope": "synthetic storage reads; no molecular solving or replay",
                "python": platform.python_version(),
                "records": args.records,
                "record_bytes": 100,
                "ordered_records_digest": expected,
                "seconds": observations,
                "median_seconds": {
                    name: {scope: statistics.median(values) for scope, values in scopes.items()}
                    for name, scopes in observations.items()
                },
                "select_statements": selects,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
