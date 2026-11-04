"""Transient single-molecule exploration; all molecular decisions use the public facade."""

import copy
import json
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from hop_design import construction


class VariantSession:
    _cache_limit = 64

    def __init__(
        self, source: Path, output: Path, *, designs: construction.DesignChoices | None = None
    ):
        self.designs = designs
        start = time.perf_counter()
        self.pool = construction.load_scaffold_exploration(source)
        self.source = source.resolve()
        self._choices = construction.query_scaffold_variants(
            self.pool,
            {
                "result_digest": self.pool.result_digest,
                "stage": "hairpin",
                "focus": "loop",
            },
        )
        self.root = self._choices.write(output).resolve()
        self._lock = threading.RLock()
        self._views: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._inspections: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._browsing: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._scene_count = 0
        self._selection_count = 0
        self._comparison: construction.ScaffoldVariantComparison | None = None
        self._envelope_revision: construction.ScaffoldEnvelopePreview | None = None
        self._state: dict[str, Any] = {
            "mode": "conditional_exploration",
            "pool": json.loads(self.pool.json_bytes),
            "choices": json.loads(self._choices.json_bytes),
            "primer_boundary_views": self._choices.primer_boundary_views,
            "preview": None,
            "selection": None,
            "comparison": None,
            "preview_status": None,
            "browsing": None,
            "timings": {"admission_seconds": time.perf_counter() - start},
        }

    def _scene_destination(self, kind: str) -> Path:
        # Evict only memory. Published receipts keep their distinct, immutable paths.
        self._scene_count += 1
        return self.root / kind / f"{self._scene_count:04d}"

    def state(self) -> dict[str, Any]:
        with self._lock:
            result = copy.deepcopy(self._state)
            result["explanation"] = self._choices.explain()
            return result

    def query(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            start = time.perf_counter()
            if self.designs is not None:
                # The public design boundary checks applicability; native queries
                # retain their own pins, preservation controls and exact eligibility.
                resolved = self.designs.query({"parameters": payload.get("parameters", [])})
                payload = {**payload, "parameters": resolved["query"]["parameters"]}
            choices = construction.query_scaffold_variants(self.pool, payload)
            self._choices = choices
            summary = json.loads(choices.json_bytes)
            preview = self._state["preview"]
            status = None
            if preview is not None:
                label = preview["option_label"]
                excluded = next(
                    (o for o in summary["excluded_options"] if o["label"] == label), None
                )
                status = {
                    "status": "excluded_by_query" if excluded else "compatible",
                    "reasons": excluded["reasons"] if excluded else [],
                }
            self._state.update(
                choices=summary,
                preview_status=status,
                selection=None,
                comparison=None,
                browsing=None,
            )
            self._comparison = None
            self._envelope_revision = None
            self._state["envelope_revision"] = None
            self._state["timings"]["query_seconds"] = time.perf_counter() - start
            return self.state()

    def _current(self, digest: Any) -> None:
        if digest != self._state["choices"]["query_digest"]:
            raise ValueError("Stale exploration query; use the current choices before continuing.")

    def evaluate_parameters(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"query_digest", "max_branches", "max_continuations_per_branch"}:
            raise ValueError("Further evaluation requires the current query and explicit bounds.")
        with self._lock:
            self._current(payload["query_digest"])
            start = time.perf_counter()
            packet = construction.evaluate_scaffold_parameters(
                self.pool,
                self._choices,
                max_branches=payload["max_branches"],
                max_continuations_per_branch=payload["max_continuations_per_branch"],
            )
            self._adopt_evaluation(packet, self._scene_destination("evaluations"))
            self._state["timings"]["evaluation_seconds"] = time.perf_counter() - start
            return self.state()

    def _adopt_evaluation(
        self,
        packet: construction.ScaffoldParameterEvaluation | construction.ScaffoldEnvelopeEvaluation,
        destination: Path,
    ) -> None:
        path = packet.write(destination)
        pool = construction.load_scaffold_exploration(path)
        query = dict(self._state["choices"]["query"])
        query["result_digest"] = pool.result_digest
        choices = construction.query_scaffold_variants(pool, query)
        self.pool, self.source, self._choices = pool, path, choices
        self._state.update(
            pool=json.loads(pool.json_bytes),
            choices=json.loads(choices.json_bytes),
            primer_boundary_views=choices.primer_boundary_views,
            evaluation=json.loads(packet.json_bytes),
            comparison=None,
            browsing=None,
        )
        self._comparison = None

    def preview_envelope(self, payload: dict[str, Any]) -> dict[str, Any]:
        from .envelope import preview_envelope

        return preview_envelope(self, payload)

    def parameter_domain(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"query_digest", "request"}:
            raise ValueError("Domain browsing requires the current query and page request.")
        with self._lock:
            self._current(payload["query_digest"])
            page = construction.query_scaffold_parameter_domain(
                self.pool, self._choices, payload["request"]
            )
            result: dict[str, Any] = json.loads(page.json_bytes)
            return result

    def evaluate_envelope(self, payload: dict[str, Any]) -> dict[str, Any]:
        from .envelope import evaluate_envelope

        return evaluate_envelope(self, payload)

    def view(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"query_digest", "option_label"} or not isinstance(
            payload["option_label"], str
        ):
            raise ValueError("A preview requires a query digest and one complete option label.")
        with self._lock:
            self._current(payload["query_digest"])
            key = (payload["query_digest"], payload["option_label"])
            if key not in self._views:
                packet = construction.project_scaffold_variant(
                    self.pool, self._choices, option_label=payload["option_label"]
                )
                path = packet.write(self._scene_destination("views"))
                relative = path.relative_to(self.root).as_posix()
                self._views[key] = {
                    **json.loads(packet.json_bytes),
                    "drawing": f"/files/{relative}/projection.svg",
                    "record": f"/files/{relative}/summary.json",
                }
            self._views.move_to_end(key)
            while len(self._views) > self._cache_limit:
                self._views.popitem(last=False)
            self._state["preview"] = self._views[key]
            return self.state()

    def select(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"query_digest", "members", "baseline"}:
            raise ValueError("Selection requires query_digest, members and baseline.")
        if (
            not isinstance(payload["members"], dict)
            or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in payload["members"].items()
            )
            or not isinstance(payload["baseline"], str)
        ):
            raise ValueError("Select explicit named preparations and a baseline member name.")
        with self._lock:
            self._current(payload["query_digest"])
            start = time.perf_counter()
            selected = construction.select_scaffold_variants(
                self.source, self._choices, members=payload["members"], baseline=payload["baseline"]
            )
            self._publish_selection(selected, list(payload["members"]), payload["query_digest"])
            self._state["timings"]["retrieval_seconds"] = time.perf_counter() - start
            return self.state()

    def _publish_selection(
        self, selected: construction.ConstructionSet, members: list[str], digest: str
    ) -> None:
        self._selection_count += 1
        path = selected.write(self.root / "selections" / f"{self._selection_count:04d}")
        archive = path.with_suffix(".zip")
        with ZipFile(archive, "x", compression=ZIP_DEFLATED) as zipped:
            for file in sorted(path.rglob("*")):
                if file.is_file():
                    info = ZipInfo(file.relative_to(path).as_posix(), (1980, 1, 1, 0, 0, 0))
                    info.compress_type = ZIP_DEFLATED
                    zipped.writestr(info, file.read_bytes())
        self._state["selection"] = {
            "members": members,
            "query_digest": digest,
            "archive": "/files/" + archive.relative_to(self.root).as_posix(),
        }

    def compare(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._current(payload.get("query_digest"))
            packet = construction.compare_scaffold_variants(self.pool, self._choices, payload)
            self._comparison = packet
            self._state["comparison"] = json.loads(packet.json_bytes)
            return self.state()

    def select_comparison(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"query_digest", "request_digest", "set_label", "baseline"} or not all(
            isinstance(v, str) for v in payload.values()
        ):
            raise ValueError(
                "Required-set selection names current query, comparison, set and baseline."
            )
        with self._lock:
            self._current(payload["query_digest"])
            if (
                self._comparison is None
                or payload["request_digest"] != self._state["comparison"]["request_digest"]
            ):
                raise ValueError("Stale required comparison; assess the current members first.")
            start = time.perf_counter()
            selected = construction.select_scaffold_variant_comparison(
                self.source,
                self._comparison,
                set_label=payload["set_label"],
                baseline=payload["baseline"],
            )
            group = next(
                g for g in self._state["comparison"]["sets"] if g["label"] == payload["set_label"]
            )
            self._publish_selection(selected, list(group["members"]), payload["query_digest"])
            self._state["selection"]["comparison_digest"] = payload["request_digest"]
            self._state["selection"]["set_label"] = payload["set_label"]
            self._state["timings"]["retrieval_seconds"] = time.perf_counter() - start
            return self.state()

    def inspect(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._current(payload.get("query_digest"))
            key = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            start = time.perf_counter()
            if key not in self._inspections:
                packet = construction.inspect_scaffold_variant(self.pool, self._choices, payload)
                path = packet.write(self._scene_destination("inspections"))
                relative = path.relative_to(self.root).as_posix()
                self._inspections[key] = {
                    **json.loads(packet.json_bytes),
                    "teaching_drawing": f"/files/{relative}/overview.svg",
                    "drawing": f"/files/{relative}/projection.svg",
                    "record": f"/files/{relative}/summary.json",
                }
            self._inspections.move_to_end(key)
            while len(self._inspections) > self._cache_limit:
                self._inspections.popitem(last=False)
            self._state["preview"] = self._inspections[key]
            self._state["preview_status"] = {"status": "compatible", "reasons": []}
            self._state["timings"]["inspection_seconds"] = time.perf_counter() - start
            return self.state()

    def browse(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Browsing preserves the query, comparison and retrieved membership."""
        with self._lock:
            self._current(payload.get("query_digest"))
            key = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            start = time.perf_counter()
            if key not in self._browsing:
                packet = construction.preview_scaffold_variant(self.pool, self._choices, payload)
                path = packet.write(self._scene_destination("browsing"))
                relative = path.relative_to(self.root).as_posix()
                result = json.loads(packet.json_bytes)
                if result["inspection"] is not None:
                    result["inspection"].update(
                        drawing=f"/files/{relative}/projection.svg",
                        teaching_drawing=f"/files/{relative}/overview.svg",
                        record=f"/files/{relative}/summary.json",
                        request_file=f"/files/{relative}/request.json",
                    )
                self._browsing[key] = result
            self._browsing.move_to_end(key)
            while len(self._browsing) > self._cache_limit:
                self._browsing.popitem(last=False)
            result = self._browsing[key]
            self._state.update(
                browsing=result,
                preview=result["inspection"],
                preview_status={"status": result["status"], "reasons": []},
            )
            self._state["timings"]["browse_seconds"] = time.perf_counter() - start
            return self.state()

    def close(self) -> None:
        pass
