from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

import hop_design as hop
import hop_design.discovery as discovery
from hop_design.models.catalog import SiteOrientation
from hop_design.models.discovery import (
    BasalProcessingGeometryRequest,
    BasalProcessingGeometrySearchLimits,
    BasalProcessingGeometrySearchResult,
)
from hop_design.models.discovery.basal_processing import (
    BasalProcessingGeometryFeasibility,
    BasalProcessingGeometryHit,
    BasalReleaseGeometry,
    RelativeBaseDomain,
    basal_processing_geometry_id,
)


def _nicking_agent(
    name: str,
    *,
    motif: str,
    cut_offset: int,
) -> hop.NickingAgent:
    return hop.NickingAgent(
        agent_id=f"example:nicking-agent/{name}@1",
        motif_top_5to3=motif,
        nicked_strand=hop.Strand.TOP,
        cut_offset=cut_offset,
        warning_codes=(),
    )


def _catalog() -> hop.ProcessingCatalog:
    return hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/basal-geometry@1",
        nicking_agents=(
            _nicking_agent("compatible", motif="ANNNN", cut_offset=5),
            _nicking_agent("post-domain", motif="ANNNNCG", cut_offset=5),
            _nicking_agent("release-conflict", motif="GGGGNNNN", cut_offset=8),
            _nicking_agent("post-uncovered", motif="ANNNNAAA", cut_offset=5),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/four-base-scar@1",
                motif_top_5to3="CCAA",
                top_cut_offset=4,
                bottom_cut_offset=8,
                warning_codes=(),
            ),
        ),
    )


def _request(
    *,
    retained_scar_template: str = "NNNN",
    post_nick_template: str = "NN",
    post_nick_domain_mode: str = "preserve",
) -> BasalProcessingGeometryRequest:
    return BasalProcessingGeometryRequest(
        release_agent_id="example:release-agent/four-base-scar@1",
        release_orientation=SiteOrientation.FORWARD,
        terminal_nicked_strand=hop.Strand.TOP,
        retained_scar_template=retained_scar_template,
        post_nick_template=post_nick_template,
        post_nick_domain_mode=post_nick_domain_mode,
        require_release_site_excised=True,
    )


def _search(**request_overrides: str) -> BasalProcessingGeometrySearchResult:
    return discovery.search_basal_processing_geometries(
        catalog=_catalog(),
        request=_request(**request_overrides),
        limits=BasalProcessingGeometrySearchLimits(
            max_search_nodes=4,
            max_hits=4,
        ),
    )


def test_basal_processing_geometry_reports_complete_signed_coordinate_audit() -> None:
    result = _search()

    assert result.status == "complete"
    assert result.release.site_start == -4
    assert result.release.site_end == 0
    assert result.release.top_cut == 0
    assert result.release.bottom_cut == 4
    assert result.release.recognition_site_excised is True
    assert result.candidate_space_size == 4
    assert result.search_nodes_examined == 4
    assert result.observed_hit_count == 1
    assert [hit.nicking_agent_id for hit in result.hits] == ["example:nicking-agent/compatible@1"]

    hit = result.hits[0]
    assert hit.canonical_ordinal == 1
    assert hit.nick_boundary == 4
    assert hit.nick_site_start == -1
    assert hit.nick_site_end == 4
    assert hit.feasible_scar_count == 256
    assert [domain.relative_coordinate for domain in hit.retained_scar_domains] == [0, 1, 2, 3]
    assert all(domain.allowed_bases == ("A", "C", "G", "T") for domain in hit.retained_scar_domains)

    audit = {row.nicking_agent_id: row for row in result.feasibility}
    assert audit["example:nicking-agent/compatible@1"].blockers == ()
    assert audit["example:nicking-agent/post-domain@1"].blockers == ("post_nick_domain_narrowed",)
    assert audit["example:nicking-agent/release-conflict@1"].blockers == (
        "release_nick_domain_conflict",
    )
    assert audit["example:nicking-agent/post-uncovered@1"].blockers == (
        "post_nick_domain_uncovered",
        "post_nick_domain_narrowed",
    )


def test_post_nick_domain_policy_is_explicit_not_a_hidden_degeneracy_rule() -> None:
    result = _search(post_nick_domain_mode="compatible")

    assert result.status == "complete"
    assert [hit.nicking_agent_id for hit in result.hits] == [
        "example:nicking-agent/compatible@1",
        "example:nicking-agent/post-domain@1",
    ]
    narrowed = result.hits[1]
    post_domains = {
        domain.relative_coordinate: domain.allowed_bases for domain in narrowed.post_nick_domains
    }
    assert post_domains == {4: ("C",), 5: ("G",)}


def test_basal_processing_geometry_reports_bounds_and_infeasibility_truthfully() -> None:
    node_limited = discovery.search_basal_processing_geometries(
        catalog=_catalog(),
        request=_request(),
        limits=BasalProcessingGeometrySearchLimits(max_search_nodes=1, max_hits=4),
    )
    hit_limited = discovery.search_basal_processing_geometries(
        catalog=_catalog(),
        request=_request(post_nick_domain_mode="compatible"),
        limits=BasalProcessingGeometrySearchLimits(max_search_nodes=4, max_hits=1),
    )
    infeasible_catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/infeasible-basal-geometry@1",
        nicking_agents=(_nicking_agent("scar-conflict", motif="AAAAAT", cut_offset=5),),
        release_agents=_catalog().release_agents,
    )
    infeasible = discovery.search_basal_processing_geometries(
        catalog=infeasible_catalog,
        request=_request(retained_scar_template="CCCC"),
        limits=BasalProcessingGeometrySearchLimits(max_search_nodes=4, max_hits=4),
    )

    assert node_limited.status == "truncated"
    assert node_limited.truncated_by == ("max_search_nodes",)
    assert hit_limited.status == "truncated"
    assert hit_limited.truncated_by == ("max_hits",)
    assert infeasible.status == "infeasible"
    assert infeasible.hits == ()
    assert infeasible.search_nodes_examined == infeasible.candidate_space_size


def test_basal_processing_geometry_fails_fast_for_catalog_and_release_contract_errors() -> None:
    with pytest.raises(ValueError, match="release agent"):
        discovery.search_basal_processing_geometries(
            catalog=_catalog(),
            request=_request().model_copy(
                update={"release_agent_id": "example:release-agent/missing@1"}
            ),
            limits=BasalProcessingGeometrySearchLimits(max_search_nodes=4, max_hits=4),
        )
    with pytest.raises(ValueError, match="four-nucleotide retained scar"):
        discovery.search_basal_processing_geometries(
            catalog=_catalog().model_copy(
                update={
                    "release_agents": (
                        hop.ReleaseAgent(
                            agent_id="example:release-agent/four-base-scar@1",
                            motif_top_5to3="CCAA",
                            top_cut_offset=4,
                            bottom_cut_offset=7,
                            warning_codes=(),
                        ),
                    )
                }
            ),
            request=_request(),
            limits=BasalProcessingGeometrySearchLimits(max_search_nodes=4, max_hits=4),
        )
    with pytest.raises(ValueError, match="is not a release agent"):
        discovery.search_basal_processing_geometries(
            catalog=_catalog(),
            request=_request().model_copy(
                update={"release_agent_id": "example:nicking-agent/compatible@1"}
            ),
            limits=BasalProcessingGeometrySearchLimits(max_search_nodes=4, max_hits=4),
        )
    with pytest.raises(ValueError, match="does not excise"):
        discovery.search_basal_processing_geometries(
            catalog=hop.ProcessingCatalog(
                catalog_id="example:processing-catalog/unexcised-release@1",
                nicking_agents=_catalog().nicking_agents,
                release_agents=(
                    hop.ReleaseAgent(
                        agent_id="example:release-agent/unexcised@1",
                        motif_top_5to3="NNNN",
                        top_cut_offset=0,
                        bottom_cut_offset=4,
                        warning_codes=(),
                    ),
                ),
            ),
            request=_request().model_copy(
                update={"release_agent_id": "example:release-agent/unexcised@1"}
            ),
            limits=BasalProcessingGeometrySearchLimits(max_search_nodes=4, max_hits=4),
        )


def test_reverse_release_orientation_uses_the_same_signed_cut_origin() -> None:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/reverse-release@1",
        nicking_agents=(_nicking_agent("compatible", motif="ANNNN", cut_offset=5),),
        release_agents=_catalog().release_agents,
    )
    request = _request(
        post_nick_template="NNNN",
        post_nick_domain_mode="compatible",
    ).model_copy(update={"release_orientation": SiteOrientation.REVERSE})

    result = discovery.search_basal_processing_geometries(
        catalog=catalog,
        request=request,
        limits=BasalProcessingGeometrySearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "complete"
    assert result.release.oriented_motif_top_5to3 == "TTGG"
    assert (result.release.site_start, result.release.site_end) == (4, 8)
    assert (result.release.top_cut, result.release.bottom_cut) == (0, 4)
    assert {
        domain.relative_coordinate: domain.allowed_bases
        for domain in result.hits[0].post_nick_domains
    } == {4: ("T",), 5: ("T",), 6: ("G",), 7: ("G",)}


def test_reverse_nick_orientation_and_post_domain_conflict_are_explicit() -> None:
    reverse_request = _request(
        post_nick_template="NNNNN",
        post_nick_domain_mode="compatible",
    ).model_copy(update={"terminal_nicked_strand": hop.Strand.BOTTOM})
    reverse = discovery.search_basal_processing_geometries(
        catalog=hop.ProcessingCatalog(
            catalog_id="example:processing-catalog/reverse-nick@1",
            nicking_agents=(_nicking_agent("compatible", motif="ANNNN", cut_offset=5),),
            release_agents=_catalog().release_agents,
        ),
        request=reverse_request,
        limits=BasalProcessingGeometrySearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert reverse.status == "complete"
    assert reverse.hits[0].orientation is SiteOrientation.REVERSE
    assert reverse.hits[0].oriented_motif_top_5to3 == "NNNNT"
    assert (reverse.hits[0].nick_site_start, reverse.hits[0].nick_site_end) == (4, 9)

    conflict = discovery.search_basal_processing_geometries(
        catalog=hop.ProcessingCatalog(
            catalog_id="example:processing-catalog/post-conflict@1",
            nicking_agents=(_nicking_agent("post-domain", motif="ANNNNCG", cut_offset=5),),
            release_agents=_catalog().release_agents,
        ),
        request=_request(post_nick_template="TT", post_nick_domain_mode="compatible"),
        limits=BasalProcessingGeometrySearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert conflict.status == "infeasible"
    assert conflict.feasibility[0].blockers == ("post_nick_domain_conflict",)


def test_basal_processing_geometry_contract_rejects_drift() -> None:
    result = _search()
    data = result.model_dump(mode="json")
    data["hits"][0]["candidate_id"] = "hop:basal-processing-geometry/" + "0" * 64 + "@1"
    with pytest.raises(ValidationError, match="candidate_id"):
        BasalProcessingGeometrySearchResult.model_validate_json(json.dumps(data))

    data = result.model_dump(mode="json")
    data["feasibility"][0]["compatible"] = False
    with pytest.raises(ValidationError, match="compatible"):
        BasalProcessingGeometrySearchResult.model_validate_json(json.dumps(data))

    data = result.model_dump(mode="json")
    data["search_nodes_examined"] = 3
    data["feasibility"] = data["feasibility"][:3]
    data["status"] = "truncated"
    data["truncated_by"] = ["max_search_nodes"]
    with pytest.raises(ValidationError, match="exhaust the available node budget"):
        BasalProcessingGeometrySearchResult.model_validate_json(json.dumps(data))


def test_basal_processing_request_is_strict_and_requires_explicit_domains() -> None:
    request = _request(retained_scar_template="nnnn", post_nick_template="nn")
    assert request.retained_scar_template == "NNNN"
    assert request.post_nick_template == "NN"

    with pytest.raises(ValidationError, match="four nucleotides"):
        _request(retained_scar_template="NNN")
    with pytest.raises(ValidationError):
        BasalProcessingGeometryRequest.model_validate(
            {
                **request.model_dump(mode="json"),
                "hidden_downstream_policy": True,
            }
        )


def test_geometry_component_contracts_reject_malformed_domains_and_release_evidence() -> None:
    with pytest.raises(ValidationError, match="canonical lexical order"):
        RelativeBaseDomain(relative_coordinate=0, allowed_bases=("C", "A"))
    with pytest.raises(ValidationError, match="DNA sequence"):
        BasalProcessingGeometryRequest.model_validate_json(
            json.dumps(
                {
                    **_request().model_dump(mode="json"),
                    "retained_scar_template": 7,
                }
            )
        )
    with pytest.raises(ValidationError, match="DNA sequence"):
        BasalProcessingGeometryRequest.model_validate_json(
            json.dumps(
                {
                    **_request().model_dump(mode="json"),
                    "post_nick_template": 7,
                }
            )
        )

    release = _search().release.model_dump(mode="json")
    release_mutations = (
        {**release, "oriented_motif_top_5to3": 7},
        {**release, "site_end": 1},
        {**release, "bottom_cut": 3},
        {**release, "recognition_site_excised": False},
    )
    for payload in release_mutations:
        with pytest.raises(ValidationError):
            BasalReleaseGeometry.model_validate_json(json.dumps(payload))


def test_feasibility_contract_rejects_structural_and_accounting_drift() -> None:
    result = _search()
    row = result.feasibility[0].model_dump(mode="json")
    invalid_rows = []

    payload = json.loads(json.dumps(row))
    payload["oriented_motif_top_5to3"] = 7
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["nick_site_end"] += 1
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["nick_boundary"] = 3
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["retained_scar_domains"][0]["relative_coordinate"] = -1
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["resolved_domains"] = list(reversed(payload["resolved_domains"]))
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["resolved_domains"][1]["relative_coordinate"] = payload["resolved_domains"][0][
        "relative_coordinate"
    ]
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["feasible_scar_count"] -= 1
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["compatible"] = False
    invalid_rows.append(payload)

    blocked = result.feasibility[2].model_dump(mode="json")
    payload = json.loads(json.dumps(blocked))
    payload["blockers"].append(payload["blockers"][0])
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(blocked))
    payload["blockers"] = list(reversed(payload["blockers"]))
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["retained_scar_domains"][0]["allowed_bases"] = []
    payload["feasible_scar_count"] = 0
    invalid_rows.append(payload)
    payload = json.loads(json.dumps(row))
    payload["blockers"] = ["retained_scar_domain_empty"]
    payload["compatible"] = False
    invalid_rows.append(payload)

    for payload in invalid_rows:
        with pytest.raises(ValidationError):
            BasalProcessingGeometryFeasibility.model_validate_json(json.dumps(payload))


def test_hit_and_result_contracts_reject_false_terminal_claims() -> None:
    preserve = _search()
    blocked_row = preserve.feasibility[1]
    with pytest.raises(ValidationError, match="must be compatible"):
        BasalProcessingGeometryHit(
            **blocked_row.model_dump(mode="python"),
            candidate_id=basal_processing_geometry_id(blocked_row),
            canonical_ordinal=1,
        )

    complete = _search(post_nick_domain_mode="compatible")
    mutations = []
    payload = complete.model_dump(mode="json")
    payload["feasibility"] = payload["feasibility"][:-1]
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["feasibility"] = list(reversed(payload["feasibility"]))
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["observed_hit_count"] -= 1
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["hits"] = payload["hits"][:-1]
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["hits"][0]["canonical_ordinal"] = 2
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["hits"] = list(reversed(payload["hits"]))
    for canonical_ordinal, hit in enumerate(payload["hits"], start=1):
        hit["canonical_ordinal"] = canonical_ordinal
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["truncated_by"] = ["max_hits"]
    payload["status"] = "truncated"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["status"] = "infeasible"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["release"]["release_agent_id"] = "example:release-agent/other@1"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["request"]["release_orientation"] = "reverse"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["feasibility"][0]["release_agent_id"] = "example:release-agent/other@1"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["feasibility"][0]["nicked_strand"] = "bottom"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["feasibility"][0]["post_nick_domains"][0]["relative_coordinate"] = 3
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["request"]["retained_scar_template"] = "CCCC"
    mutations.append(payload)
    payload = complete.model_dump(mode="json")
    payload["request"]["post_nick_domain_mode"] = "preserve"
    mutations.append(payload)

    no_hits = _search().model_dump(mode="json")
    no_hits["feasibility"][0]["blockers"] = ["post_nick_domain_narrowed"]
    no_hits["feasibility"][0]["compatible"] = False
    no_hits["hits"] = []
    no_hits["observed_hit_count"] = 0
    mutations.append(no_hits)

    incomplete_infeasible = _search().model_dump(mode="json")
    incomplete_infeasible["candidate_space_size"] += 1
    incomplete_infeasible["status"] = "infeasible"
    incomplete_infeasible["hits"] = []
    incomplete_infeasible["observed_hit_count"] = 0
    incomplete_infeasible["feasibility"][0]["blockers"] = ["post_nick_domain_narrowed"]
    incomplete_infeasible["feasibility"][0]["compatible"] = False
    incomplete_infeasible["truncated_by"] = ["max_search_nodes"]
    mutations.append(incomplete_infeasible)

    unexcised = _search().model_dump(mode="json")
    unexcised["release"]["site_start"] = 0
    unexcised["release"]["site_end"] = 4
    unexcised["release"]["oriented_motif_top_5to3"] = "NNNN"
    unexcised["release"]["recognition_site_excised"] = False
    mutations.append(unexcised)

    for payload in mutations:
        with pytest.raises(ValidationError):
            BasalProcessingGeometrySearchResult.model_validate_json(json.dumps(payload))
