"""Conditional survey browser state; molecular authority remains the public facade."""

import copy
import json
import threading
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from hop_design import construction

from ...design_commands import design_commands


def _state_key(value: Any) -> str:
    """Identify browser state only; molecular identities remain facade-owned."""
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class SurveySession:
    """Browse an admitted snapshot; search and requirement relaxation are separate actions."""

    def __init__(
        self,
        request: Path,
        index: Path,
        output: Path,
        *,
        discovery: dict[str, Any] | None = None,
        designs: construction.DesignChoices | None = None,
    ):
        self.designs = designs
        self.pool = construction.load_interface_survey_choices(request, index)
        self.request, self.index = request.resolve(), index.resolve()
        if any(p.is_symlink() for p in (output, *output.parents)):
            raise ValueError("Survey browser output cannot use symbolic links.")
        output.mkdir(parents=True, exist_ok=False)
        self.root = output.resolve()
        self._lock = threading.RLock()
        self._serial = 0
        self._views: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._state: dict[str, Any] = {
            "mode": "interface_survey",
            "discovery": copy.deepcopy(discovery),
            "choices": (self.designs or self.pool).query(),
            "parameter_key": self._parameter_key(self.pool),
            "preview": None,
            "preview_status": None,
            "selection": None,
            "handoff": None,
            "sample_seed": None,
        }
        self._token()

    def _parameter_key(self, pool: construction.InterfaceSurveyChoices) -> str:
        key = _state_key(pool.parameter_key())
        directory = self.root / "definitions"
        directory.mkdir(exist_ok=True)
        path = directory / f"{key}.svg"
        data = pool.parameter_key_svg_bytes
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("Published parameter definition drawing changed.")
        else:
            with path.open("xb") as output:
                output.write(data)
        return "/files/" + path.relative_to(self.root).as_posix()

    def _token(self) -> None:
        choices = self._state["choices"]
        self._state["token"] = _state_key([choices["snapshot_digest"], choices["query_digest"]])

    def _check(self, payload: dict[str, Any], fields: set[str]) -> None:
        if set(payload) != fields | {"token"}:
            raise ValueError("Survey action has missing or unknown fields.")
        if payload["token"] != self._state["token"]:
            raise ValueError("Stale survey choices; use the current snapshot and query.")

    def state(self) -> dict[str, Any]:
        with self._lock:
            result = copy.deepcopy(self._state)
            if self.designs is not None:
                result["explanation"] = self.designs.explain(result["choices"]["query"])
                query_path = self._command_query(result["choices"]["query"])
                directory = self.request.parent.parent
                result["command_context"] = {"directory": str(directory), "query": str(query_path)}
                result["commands"] = design_commands(
                    directory,
                    query_path,
                    result["explanation"],
                    selection=result["selection"],
                    seed=result["sample_seed"],
                )
            preview = result["preview"]
            identity = (
                None
                if preview is None
                else preview["summary"]["selection"]["materialized_realization_id"]
            )
            result["plot_svg"] = (
                (self.designs or self.pool)
                .plot_svg_bytes(result["choices"]["query"], selected_identity=identity)
                .decode()
            )
            return result

    def _command_query(self, query: dict[str, Any]) -> Path:
        """Bind copied commands to an immutable applied query in this local session."""
        content = json.dumps(query, sort_keys=True, indent=2).encode()
        folder = self.root / "queries"
        folder.mkdir(exist_ok=True)
        path = folder / (_state_key(query) + ".json")
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError("Published command query changed.")
        else:
            with path.open("xb") as handle:
                handle.write(content)
        return path

    def _rebind(self) -> None:
        """Keep the inspected molecule; independently bind eligibility to the new query."""
        self._state.update(selection=None, handoff=None, sample_seed=None)
        preview = self._state["preview"]
        if preview is None:
            return
        previous = preview["summary"]["selection"]
        try:
            selected = self._select(previous["address"], previous["materialized_realization_id"])
        except ValueError:
            self._state["preview_status"] = "excluded_by_query"
        else:
            self._show(selected)

    def _adopt(
        self,
        pool: construction.InterfaceSurveyChoices,
        choices: dict[str, Any],
        designs: construction.DesignChoices | None,
    ) -> None:
        # A failed replay/publication must not leave the client with a stale action token.
        previous_pool, previous_state, previous_designs = self.pool, self._state, self.designs
        self._state = copy.deepcopy(previous_state)
        try:
            self.pool = pool
            self.designs = designs
            self._state["choices"] = choices
            self._state["parameter_key"] = self._parameter_key(pool)
            self._token()
            self._rebind()
        except BaseException:
            self.pool, self._state, self.designs = previous_pool, previous_state, previous_designs
            raise

    def query(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, {"query"})
            if not isinstance(payload["query"], dict):
                raise ValueError("A survey query must be an object.")
            choices = (self.designs or self.pool).query(payload["query"])
            self._adopt(self.pool, choices, self.designs)
            return self.state()

    def reload(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, set())
            pool = construction.load_interface_survey_choices(self.request, self.index)
            designs = (
                construction.load_design_choices(self.request.parent.parent)
                if self.designs is not None
                else None
            )
            self._adopt(pool, (designs or pool).query(self._state["choices"]["query"]), designs)
            return self.state()

    def _destination(self, kind: str) -> Path:
        self._serial += 1
        return self.root / kind / f"{self._serial:06d}"

    def _show(self, selected: dict[str, Any]) -> dict[str, Any]:
        reference = None
        preview = self._state["preview"]
        if preview is not None:
            summary = preview["summary"]
            previous = summary["selection"]
            reference = (
                summary.get("reference_selection")
                if previous["materialized_realization_id"]
                == selected["materialized_realization_id"]
                else previous
            )
        # Query rebinding and repeated selection keep the same comparison.
        # A different preparation compares against the previously displayed one.
        if selected.get("schema") == "hop.insert-design-selection/v1":
            reference = selected["reference"]
        key = _state_key([reference, selected])
        if key not in self._views:
            packet = (
                self.designs.atlas(selected, reference_selection=reference)
                if self.designs
                else construction.inspect_interface_survey_atlas(
                    self.request, self.index, selection=selected, reference_selection=reference
                )
            )
            path = packet.write(self._destination("atlases"), print_pages=False)
            relative = path.relative_to(self.root).as_posix()
            self._views[key] = {
                "summary": json.loads(packet.json_bytes),
                "drawing": f"/files/{relative}/projection.svg",
                "teaching": f"/files/{relative}/overview.svg",
                "record": f"/files/{relative}/summary.json",
            }
        self._views.move_to_end(key)
        while len(self._views) > 8:
            self._views.popitem(last=False)
        self._state.update(
            selection=selected, preview=self._views[key], preview_status="compatible", handoff=None
        )
        return self.state()

    def select(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, {"target", "step", "materialized_realization_id"})
            selected = self._select(
                {"target": payload["target"], "step": payload["step"]},
                payload["materialized_realization_id"],
            )
            result = self._show(selected)
            self._state["sample_seed"] = None
            result["sample_seed"] = None
            return result

    def sample(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, {"seed"})
            selected = (self.designs or self.pool).sample(
                seed=payload["seed"], query=self._state["choices"]["query"]
            )
            self._show(selected)
            self._state["sample_seed"] = payload["seed"]
            return self.state()

    def retrieve(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check(payload, {"selection"})
            selected = self._state["selection"]
            if selected is None or payload["selection"] != selected:
                raise ValueError("Select an exact eligible preparation before retrieving it.")
            path = self._destination("preparations")
            if self.designs is not None:
                self.designs.retrieve(selected, path)
            else:
                construction.retrieve_interface_survey_witness(
                    self.request, self.index, selection=selected, destination=path
                )
            archive = path.with_suffix(".zip")
            with ZipFile(archive, "x", compression=ZIP_DEFLATED) as zipped:
                for file in sorted(path.rglob("*")):
                    if file.is_file():
                        info = ZipInfo(file.relative_to(path).as_posix(), (1980, 1, 1, 0, 0, 0))
                        info.compress_type = ZIP_DEFLATED
                        zipped.writestr(info, file.read_bytes())
            self._state["handoff"] = {
                "selection": selected,
                "directory": path.relative_to(self.root).as_posix(),
                "archive": "/files/" + archive.relative_to(self.root).as_posix(),
            }
            return self.state()

    def close(self) -> None:
        pass

    def _select(self, address: dict[str, int], identity: str) -> dict[str, Any]:
        query = self._state["choices"]["query"]
        if self.designs is not None:
            return self.designs.select(
                {"address": address, "materialized_realization_id": identity}, query=query
            )
        return self.pool.select(**address, materialized_realization_id=identity, query=query)
