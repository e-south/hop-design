"""Finite witnesses, not independent parts, determine conditional alternatives."""

import json

import pytest

from hop_design.design.construction.variants.query import query_summary
from hop_design.models.construction.variants.query import ScaffoldVariantQuery

DIGEST = "sha256:" + "a" * 64


def query(**kwargs):
    return ScaffoldVariantQuery.model_validate_json(
        json.dumps(
            {
                "result_digest": DIGEST,
                "stage": "hairpin",
                "focus": "loop",
                **kwargs,
            }
        )
    )


def option(label, loop, closing, endpoint):
    def variant(word):
        return {"variant_id": "sha256:" + word * 64, "sequences": [{"sequence": word}]}

    neighborhoods = {
        "loop": variant(loop),
        "closing": variant(closing),
        "assembly": variant("e"),
        "stem": variant("f"),
        "interfaces": {"variant_id": "sha256:" + "0" * 64, "sequences": []},
    }
    return {
        "label": label,
        "materialized_realization_id": f"hop:materialized-construction/{label * 64}@1",
        "molecular_identity": {"hairpin": label, "endpoint": endpoint},
        "material_roles": {"source": label},
        "interface": None,
        "methods": [],
        "variants": {
            "hairpin": dict(neighborhoods),
            "endpoint": dict(neighborhoods),
        },
    }


def pool():
    metadata = {
        "result_digest": DIGEST,
        "coverage": {"exploration_complete": False},
        "examined_failures": [{"status": "failed_examined_preparation"}],
        "local_coverage": [{"status": "exhausted"}],
        "producer": {},
    }
    return metadata, [
        option("a", "a", "c", "p"),
        option("b", "b", "d", "p"),
        option("c", "b", "c", "q"),
    ]


def test_focus_replacement_keeps_other_pins_and_never_synthesizes_parts():
    pins = [
        {"neighborhood": "loop", "variant_ids": ["sha256:" + "a" * 64]},
        {"neighborhood": "closing", "variant_ids": ["sha256:" + "d" * 64]},
    ]
    result = query_summary(*pool(), query(pins=pins))
    assert result["compatible_options"] == []
    assert result["status"] == "no_compatible_options_in_evaluated_pool"
    assert result["variants"][0]["option_labels"] == ["b"]
    assert result == query_summary(*pool(), query(pins=list(reversed(pins))))
    assert result["coverage"]["exploration_complete"] is False
    assert result["examined_failures"] and result["local_coverage"]
    assert result["selected_product"] is None


def test_stage_groups_preserve_duplicate_preparations_and_fixed_reference():
    result = query_summary(
        *pool(),
        query(
            stage="endpoint",
            reference="a",
            controls=[
                {"stage": "endpoint", "property": "product_identity"},
            ],
        ),
    )
    assert result["products"] == [
        {"stage": "endpoint", "molecule_id": "p", "option_labels": ["a", "b"]}
    ]
    assert result["query"]["reference"] == "a"
    assert result["excluded_options"][0]["label"] == "c"
    assert result["excluded_options"][0]["reasons"][0]["kind"] == "preserved_property"


@pytest.mark.parametrize(
    "change, message",
    [
        ({"result_digest": "sha256:" + "b" * 64}, "Stale"),
        ({"reference": "absent"}, "reference"),
        ({"pins": [{"neighborhood": "loop", "variant_ids": ["sha256:" + "f" * 64]}]}, "Unknown"),
        ({"controls": [{"stage": "hairpin", "property": "product_identity"}]}, "reference"),
        ({"silently_relax": True}, "Extra inputs"),
    ],
)
def test_query_fails_closed(change, message):
    with pytest.raises(ValueError, match=message):
        query_summary(*pool(), query(**change))


def test_unknown_region_correspondence_is_not_reported_as_unchanged():
    metadata, options = pool()
    for option in options:
        option["variants"]["endpoint"]["loop"] = None
    result = query_summary(metadata, options, query(stage="endpoint", reference="a"))
    assert result["variants"] == []
    assert result["changes"][0]["status"] == "partly_unassessed"
    assert result["changes"][0]["unassessed_neighborhoods"] == ["loop"]


def test_preserved_surroundings_are_stage_qualified_and_independent_of_browsing_focus():
    intent = query(
        reference="a", surroundings=[{"stage": "hairpin", "except_neighborhood": "loop"}]
    )
    result = query_summary(*pool(), intent)
    assert result["compatible_options"] == ["a", "c"]
    assert result["excluded_options"][0]["reasons"][0] == {
        "kind": "preserved_surroundings",
        "stage": "hairpin",
        "neighborhood": "closing",
        "status": "different",
    }
    changed_focus = intent.model_copy(update={"focus": "assembly"})
    assert query_summary(*pool(), changed_focus)["compatible_options"] == ["a", "c"]
    with pytest.raises(ValueError, match="reference"):
        query(surroundings=[{"stage": "hairpin", "except_neighborhood": "loop"}])


def test_unknown_surroundings_cannot_be_preserved_by_equal_absence():
    metadata, options = pool()
    for candidate in options:
        candidate["variants"]["hairpin"]["closing"] = None
    result = query_summary(
        metadata,
        options,
        query(reference="a", surroundings=[{"stage": "hairpin", "except_neighborhood": "loop"}]),
    )
    assert result["compatible_options"] == []
    assert result["excluded_options"][0]["reasons"][0]["status"] == "unassessed"


def test_parameter_brushes_keep_joint_witnesses_and_condition_on_other_axes():
    metadata, options = pool()
    metadata["parameter_domains"] = {
        "foldback_arm_bp": {"values": [8, 9, 10]},
        "join_offset_nt": {"values": [1, 2]},
        "self_paired_arm_bp": {"values": [6, 7, 8, 9]},
        "left_gap": {"values": [0, 6]},
        "right_gap": {"values": [0, 6]},
    }
    for candidate, (arm, displacement, gap) in zip(
        options, [(8, 1, 0), (9, 1, 6), (9, 2, 6)], strict=True
    ):
        candidate["parameter_values"] = {
            "foldback_arm_bp": arm,
            "join_offset_nt": displacement,
            "self_paired_arm_bp": arm - displacement,
            "left_gap": gap,
            "right_gap": gap,
        }
    intent = query(
        schema="hop.scaffold-variant-query/v2",
        parameters=[
            {"key": "self_paired_arm_bp", "minimum": 7, "maximum": 7},
            {"key": "foldback_arm_bp", "values": [9]},
        ],
    )
    result = query_summary(metadata, options, intent)
    assert result["compatible_options"] == ["c"]
    space = result["choice_space"]
    assert space["availability"]["self_paired_arm_bp"] == {"6": 0, "7": 1, "8": 1, "9": 0}
    assert space["availability"]["foldback_arm_bp"] == {"8": 1, "9": 1, "10": 0}
    assert next(a for a in space["axes"] if a["key"] == "foldback_arm_bp")["declared"][
        "values"
    ] == [8, 9, 10]
    assert len(space["paths"]) == 3  # no invented path for the unobserved arm of 10
    impossible_pair = query(
        schema="hop.scaffold-variant-query/v2",
        parameters=[
            {"key": "left_gap", "values": [0]},
            {"key": "right_gap", "values": [6]},
        ],
    )
    assert query_summary(metadata, options, impossible_pair)["compatible_options"] == []


def test_parameter_constraints_require_explicit_version_and_unique_keys():
    with pytest.raises(ValueError, match="v2"):
        query(parameters=[{"key": "join_offset_nt", "values": [2]}])
    with pytest.raises(ValueError, match="once"):
        query(
            schema="hop.scaffold-variant-query/v2",
            parameters=[
                {"key": "join_offset_nt", "values": [1]},
                {"key": "join_offset_nt", "values": [2]},
            ],
        )


def test_preserved_controls_dim_context_paths_without_removing_the_available_network():
    result = query_summary(
        *pool(),
        query(
            stage="endpoint",
            reference="a",
            controls=[{"stage": "endpoint", "property": "product_identity"}],
        ),
    )
    paths = result["choice_space"]["paths"]
    assert [p["option_label"] for p in paths] == ["a", "b", "c"]
    assert [p["option_label"] for p in paths if p["eligible_under_preserved_controls"]] == [
        "a",
        "b",
    ]
    assert result["compatible_options"] == ["a", "b"]
