"""User intent is optional; resolved construction permissions are explicit."""

import json

from hop_design import construction

STEM = "ATAACTTCGTATAGCATACATTATACGAAGTTAT"


def test_unspecified_ends_remain_open_and_default_permissions_are_inspectable():
    request = {"stem_arm": STEM, "product": "released_insert"}
    prepared = construction.resolve_design_request(request)
    result = json.loads(prepared.json_bytes)
    assert request == {"stem_arm": STEM, "product": "released_insert"}
    assert result["intent"]["ends"] is None
    effective = result["effective_request"]
    assert effective["stem_arm"] == STEM
    assert effective["targets"] == {"left_words": None, "right_words": None}
    assert result["context"]["id"] == "linear-source/v2"
    assert result["context"]["digest"].startswith("sha256:")
    assert result["provenance"]["stem_arm"] == "user"
    assert result["provenance"]["foldback"] == "context"
    assert effective["foldback"]["geometry"].get("loop_sequences") is None
    assert len(effective["foldback"]["geometry"]["loop_lengths_nt"]) > 1
    assert len(effective["foldback"]["geometry"]["annealing_arm_lengths_bp"]) > 1
    assert result["search_required"] is True


def test_one_or_both_words_are_constraints_and_not_defaults():
    for words, left, right in [
        ({"left": "AGTC"}, ["AGTC"], None),
        ({"right": "AACC"}, None, ["AACC"]),
        ({"left": "AGTC", "right": "AACC"}, ["AGTC"], ["AACC"]),
    ]:
        result = json.loads(
            construction.resolve_design_request(
                {"stem_arm": STEM, "product": "released_insert", "ends": words}
            ).json_bytes
        )
        assert result["effective_request"]["targets"] == {
            "left_words": left,
            "right_words": right,
        }
        assert result["provenance"]["targets"] == "user"


def test_scaffold_intent_intersects_permissions_without_requiring_duplicate_edits():
    result = json.loads(
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "scaffold": {"loop_nt": {"minimum": 4, "maximum": 5}},
                "loop_words": ["GAAA", "TTTC"],
                "methods": {"release": ["BsaI-HFv2"]},
            }
        ).json_bytes
    )
    geometry = result["effective_request"]["foldback"]["geometry"]
    assert geometry["loop_lengths_nt"] == [4]
    assert geometry["loop_sequences"] == ["GAAA", "TTTC"]
    assert result["provenance"]["foldback"] == "user_within_context"


def test_conflicts_do_not_relax_context_or_mutate_intent():
    import pytest

    with pytest.raises(ValueError, match="loop"):
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "scaffold": {"loop_nt": {"minimum": 30, "maximum": 32}},
            }
        )
    with pytest.raises(ValueError, match=r"release.*not permitted"):
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "methods": {"release": ["unknown-enzyme"]},
            }
        )
    with pytest.raises(ValueError, match="end word"):
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "ends": {"left": ""},
            }
        )


def test_resolving_user_constraints_does_not_rewrite_the_context_identity():
    open_result = json.loads(
        construction.resolve_design_request(
            {"stem_arm": STEM, "product": "released_insert"}
        ).json_bytes
    )
    pinned = json.loads(
        construction.resolve_design_request(
            {"stem_arm": STEM, "product": "released_insert", "loop_words": ["GAAA"]}
        ).json_bytes
    )
    assert pinned["context"] == open_result["context"]
    assert pinned["permissions"] == open_result["permissions"]
    assert pinned["effective_request"] != open_result["effective_request"]


def test_release_permission_conflict_is_located_before_discovery_writes(tmp_path):
    import pytest

    resolved = json.loads(
        construction.resolve_design_request(
            {"stem_arm": STEM, "product": "released_insert"}
        ).json_bytes
    )
    context = resolved["permissions"]
    basal = context["basal"]["enzymes"]
    basal["allowed_enzyme_ids"] = ["example:enzyme/nb.bsrdi@1"]
    basal["role_restrictions"] = [
        role for role in basal["role_restrictions"] if role["role"] != "end_generation"
    ]
    destination = tmp_path / "designs"
    with pytest.raises(ValueError, match=r"Released-insert.*basal\.enzymes.*release\.enzymes"):
        construction.discover_designs(
            {"stem_arm": STEM, "product": "released_insert", "context": context},
            destination,
        )
    assert not destination.exists()


def test_mapping_resolution_writes_a_portable_create_only_request(tmp_path):
    import pytest

    packet = construction.resolve_design_request({"stem_arm": STEM, "product": "released_insert"})
    output = packet.write(tmp_path / "request")
    assert json.loads((output / "request.json").read_bytes())["targets"] == {
        "left_words": None,
        "right_words": None,
    }
    with pytest.raises(FileExistsError):
        packet.write(output)


def test_supported_hairpin_requests_do_not_acquire_release_steps_or_ends():
    for product, endpoint in [
        ("hairpin", "ssdna_hairpin"),
        ("adapter_ligated_hairpin", "adapter_ligated_hairpin"),
    ]:
        result = json.loads(
            construction.resolve_design_request({"stem_arm": STEM, "product": product}).json_bytes
        )
        effective = result["effective_request"]
        assert effective["endpoint"] == endpoint
        assert effective["ends"] is None
        assert effective["release"] is None
        assert effective["materialization"]["endpoint_auxiliaries"] is None
        assert result["context"]["origin"] == "packaged"


def test_hairpin_end_constraints_name_the_endpoint_boundary():
    import pytest

    with pytest.raises(ValueError, match="released insert"):
        construction.resolve_design_request(
            {"stem_arm": STEM, "product": "hairpin", "ends": {"left": "AAAA"}}
        )


def test_inherited_scaffold_requirements_constrain_loop_word_resolution():
    import pytest

    context = json.loads(
        construction.resolve_design_request(
            {"stem_arm": STEM, "product": "released_insert"}
        ).json_bytes
    )["permissions"]
    context["whole_route_constraints"]["hairpin_scaffold"] = {
        "loop_nt": {"minimum": 3, "maximum": 3}
    }
    with pytest.raises(ValueError, match="loop"):
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "context": context,
                "loop_words": ["GAAA"],
            }
        )


def test_public_intent_rejects_internal_schema_field_names():
    import pytest

    with pytest.raises(ValueError, match="schema"):
        construction.resolve_design_request(
            {
                "schema_id": "hop.construction-intent/v1",
                "stem_arm": STEM,
                "product": "released_insert",
            }
        )


def test_explicit_end_alternatives_are_permissions_and_never_substituted():
    result = json.loads(
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "ends": {"left": ["AGTC", "AACC"], "right": "AGTC"},
            }
        ).json_bytes
    )
    assert result["effective_request"]["targets"] == {
        "left_words": ["AACC", "AGTC"],
        "right_words": ["AGTC"],
    }


def test_joint_end_pair_rosters_are_rejected_instead_of_cartesianized():
    import pytest

    with pytest.raises(ValueError):
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "ends": {"pairs": [["AGTC", "AACC"], ["TTTT", "CCCC"]]},
            }
        )
    for value in ([], ["AAAA", "aaaa"], ["AAAA", ""]):
        with pytest.raises(ValueError):
            construction.resolve_design_request(
                {
                    "stem_arm": STEM,
                    "product": "released_insert",
                    "ends": {"left": value},
                }
            )
