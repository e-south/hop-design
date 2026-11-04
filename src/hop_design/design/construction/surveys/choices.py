"""Conditional coordinates over committed complete witnesses; no new molecular search."""

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.molecular.parameter_key import render_parameter_definition_key
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..search.diversity import diversity_summary
from .admission import open_survey
from .domains import excluded_interface_values, survey_domains
from .execute import load_request
from .figure import InterfaceSurveyFigure, survey_figure
from .index import SurveyIndex
from .parameter_key import AXIS_ORDER, CONTEXT_KEYS, parameter_key, survey_context
from .selection import load_query, matches, sample_path, select_path


def _project(
    request: InterfaceSurveyRequest,
    records: list[dict[str, Any]],
    coverage: dict[str, int],
    fully_enumerated: bool,
    query: InterfaceSurveyQuery,
    *,
    excluded_values: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    domains = survey_domains(request)
    names = {str(e.enzyme_id): e.canonical_name for e in request.enzyme_catalog.enzymes}
    keys = list(dict.fromkeys((*AXIS_ORDER, *CONTEXT_KEYS, *(p.key for p in query.parameters))))
    paths = [
        {
            **{
                k: row[k]
                for k in (
                    "address",
                    "materialized_realization_id",
                    "molecular_identity",
                    "overhead",
                    "methods",
                    "material_roles",
                )
            },
            "values": {k: row["values"][k] for k in keys if k in row["values"]},
            "matches": matches(row, query),
        }
        for row in records
    ]
    axes = []
    for key in keys:
        domain = domains.get(key, {"basis": "observed_only"})
        # Group once per axis rather than scanning the pool for every permitted
        # value, including the many values with no recorded witness.
        grouped: dict[Any, list[dict[str, Any]]] = {}
        values = set(domain.get("values", ()))
        for path in paths:
            if key in path["values"]:
                values.add(path["values"][key])
            grouped.setdefault(path["values"].get(key), []).append(path)
        nodes = []
        for value in sorted(values):
            witnesses = grouped.get(value, [])
            conditional = [
                p
                for p in witnesses
                if query.includes_preparation(p["materialized_realization_id"])
                and all(s.key == key or s.accepts(p["values"].get(s.key)) for s in query.parameters)
            ]
            nodes.append(
                {
                    "value": value,
                    "label": names.get(value, str(value)),
                    "supported_preparations": len(
                        {p["materialized_realization_id"] for p in witnesses}
                    ),
                    "conditional_preparations": len(
                        {p["materialized_realization_id"] for p in conditional}
                    ),
                    "supported_records": len(witnesses),
                    "conditional_records": len(conditional),
                    "state": "supported"
                    if conditional
                    else "supported_elsewhere"
                    if witnesses
                    else "excluded_in_scope"
                    if fully_enumerated or value in (excluded_values or {}).get(key, ())
                    else "unresolved",
                }
            )
        axes.append(
            {**parameter_definition(key).model_dump(mode="json"), "domain": domain, "nodes": nodes}
        )
    matching = [p for p in paths if p["matches"]]
    return {
        "schema": "hop.interface-survey-choices/v1",
        "validation": "index_integrity_only; aggregate_replay_separate",
        "query": query.model_dump(mode="json", by_alias=True),
        "request_digest": sha256_digest(canonical_json_bytes(request)),
        "coverage": coverage,
        "fully_enumerated": fully_enumerated,
        "enumeration_scope": request.source_context_objective,
        "all_preparations_enumerated": fully_enumerated
        and request.source_context_objective == "all_words",
        "matching_preparations": len({p["materialized_realization_id"] for p in matching}),
        "matching_records": len(matching),
        "matching_products": {
            stage: len({p["molecular_identity"][stage] for p in matching})
            for stage in ("hairpin", "endpoint")
        },
        "axes": axes,
        "paths": paths,
        "context": survey_context(request),
    }


@dataclass(frozen=True, init=False, repr=False)
class InterfaceSurveyChoices:
    """An admitted immutable coordinate snapshot; mapping queries perform no checkpoint I/O.

    Resume or replacement of the source index requires loading another snapshot.
    This object contains plotting facts, not a molecular replay certificate.
    """

    _request: InterfaceSurveyRequest
    _snapshot: bytes
    _digest: str
    _roots: tuple[ProtectedRoot, ...]
    _excluded_pairs: tuple[tuple[str, str], ...]
    _ended_pairs: tuple[tuple[str, str], ...]

    def figure(
        self,
        query: str | Path | dict[str, Any] | None = None,
        *,
        selection: str | Path | dict[str, Any] | None = None,
        display_axes: tuple[str, ...] | None = None,
    ) -> InterfaceSurveyFigure:
        """Publish the admitted landscape, optionally highlighting an exact selection."""
        return survey_figure(self, query=query, selection=selection, display_axes=display_axes)

    def parameter_key(self) -> dict[str, Any]:
        """Declare the coarse molecular vocabulary without selecting a construction."""
        return parameter_key(self._request)

    def plot_svg_bytes(
        self,
        query: str | Path | dict[str, Any] | None = None,
        *,
        selected_identity: str | None = None,
    ) -> bytes:
        """Draw this query; highlighting a previous preview does not select it for retrieval."""
        return render_survey_plot(self.query(query), selected_identity=selected_identity)

    @property
    def parameter_key_svg_bytes(self) -> bytes:
        """Standalone schematic using the same definitions as the coordinate axes."""
        return render_parameter_definition_key(self.parameter_key())

    def query(self, query: str | Path | dict[str, Any] | None = None) -> dict[str, Any]:
        intent = load_query(query)
        snapshot = json.loads(self._snapshot)
        intent.validate_membership(
            self._digest, (p["materialized_realization_id"] for p in snapshot["paths"])
        )
        result = _project(
            self._request,
            snapshot["paths"],
            snapshot["coverage"],
            snapshot["fully_enumerated"],
            intent,
            excluded_values=snapshot.get("excluded_values"),
        )
        result["query_digest"] = sha256_digest(canonical_json_bytes(intent))
        result["snapshot_digest"] = self._digest
        if objective := snapshot.get("search_objective"):
            result["search_objective"] = diversity_summary(
                DesignSearchObjective.model_validate_json(json.dumps(objective)), result["paths"]
            )
        return result

    def select(
        self,
        *,
        target: int,
        step: int,
        materialized_realization_id: str,
        query: str | Path | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Reference one exact preparation that satisfies all active predicates."""
        if type(target) is not int or type(step) is not int or target < 0 or step < 0:
            raise ValueError("Selection target and step must be nonnegative integers.")
        intent = load_query(query)
        paths = json.loads(self._snapshot)["paths"]
        intent.validate_membership(self._digest, (p["materialized_realization_id"] for p in paths))
        for path in paths:
            if (
                path["address"] == {"target": target, "step": step}
                and path["materialized_realization_id"] == materialized_realization_id
            ):
                return select_path(self._request, self._digest, path, intent)
        raise ValueError(
            "Selected exact identity and address are not a complete path in this snapshot."
        )

    def sample(
        self,
        *,
        seed: int,
        query: str | Path | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sample a matching exact preparation deterministically, without new evaluation.

        Duplicate records of one identity have one sampling weight. This is not a
        sample of the unexamined domain or of distinct endpoint products.
        """
        intent = load_query(query)
        paths = json.loads(self._snapshot)["paths"]
        intent.validate_membership(self._digest, (p["materialized_realization_id"] for p in paths))
        path = sample_path(paths, intent, seed)
        return select_path(self._request, self._digest, path, intent)


def load_interface_survey_choices(
    request_path: str | Path, index_path: str | Path
) -> InterfaceSurveyChoices:
    """Admit checkpoint integrity once and retain only compact complete-path facts."""
    roots = tuple(ProtectedRoot.capture(p) for p in (request_path, index_path))
    request, producer = load_request(request_path), producer_identity()
    index, limits = open_survey(Path(index_path), request=request, producer=producer)
    with index:
        return choices_from_admitted_index(index, limits, producer=producer, roots=roots)


def choices_from_admitted_index(
    index: SurveyIndex,
    limits: SurveyEvaluationLimits,
    *,
    producer: dict[str, str],
    roots: tuple[ProtectedRoot, ...],
) -> InterfaceSurveyChoices:
    """Project one admitted read snapshot, retaining its original producer identity."""
    request = index.request
    paths: list[dict[str, Any]] = []
    last: dict[int, bool] = {}
    ended: dict[int, bool] = {}
    evaluations = sha256()
    for target, step, content, count, _ in index.evaluations():
        record = json.loads(content)
        evaluations.update(canonical_json_bytes([target, step, sha256_digest(content)]))
        last[target] = record["next"] is None and record["exhaustion_proven"]
        ended[target] = record["next"] is None
        if (
            len(record["projections"]) != count
            or [p["materialized_realization_id"] for p in record["projections"]]
            != record["witnesses"]
        ):
            raise ValueError("Survey projections disagree with their recorded witnesses.")
        paths.extend(
            {
                "address": {"target": target, "step": step},
                "record_digest": sha256_digest(content),
                **p,
            }
            for p in record["projections"]
        )
    snapshot = canonical_json_bytes(
        {
            "paths": paths,
            "coverage": index.coverage(),
            "fully_enumerated": len(last) == request.targets.pair_count and all(last.values()),
            "evaluations_digest": "sha256:" + evaluations.hexdigest(),
            "excluded_values": excluded_interface_values(request, last, paths),
            **(
                {"search_objective": limits.objective.model_dump(mode="json")}
                if limits.objective is not None
                else {}
            ),
        }
    )
    pool = object.__new__(InterfaceSurveyChoices)
    object.__setattr__(pool, "_request", request)
    object.__setattr__(pool, "_snapshot", snapshot)
    object.__setattr__(pool, "_roots", roots)
    object.__setattr__(
        pool,
        "_ended_pairs",
        tuple(request.targets.pair_at(t) for t, done in sorted(ended.items()) if done),
    )
    supported = {p["address"]["target"] for p in paths}
    object.__setattr__(
        pool,
        "_excluded_pairs",
        tuple(
            request.targets.pair_at(target)
            for target, complete in sorted(last.items())
            if complete and target not in supported
        ),
    )
    object.__setattr__(
        pool,
        "_digest",
        sha256_digest(
            canonical_json_bytes(
                {
                    "request": request.model_dump(mode="json", by_alias=True),
                    "producer": producer,
                    "snapshot": sha256_digest(snapshot),
                }
            )
        ),
    )
    return pool


def query_interface_survey(
    request_path: str | Path,
    index_path: str | Path,
    query: str | Path | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cold file query. Retain load_interface_survey_choices() for repeated brushing."""
    return load_interface_survey_choices(request_path, index_path).query(query)
