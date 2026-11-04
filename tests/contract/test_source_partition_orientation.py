"""Source cleanup preserves the encoded payload on its actual physical strand."""

import json

import pytest
from pydantic import ValidationError

from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryRequest
from hop_design.models.sequence import reverse_complement_iupac
from tests.integration.test_source_partition_discovery import _request


def mirrored_request():
    document = _request().model_dump(mode="json", by_alias=True)
    source = document["source"]
    sequence = source["top_sequence_5prime"]
    source["top_sequence_5prime"] = reverse_complement_iupac(sequence)
    for end in ("five_prime_end", "three_prime_end"):
        source[f"top_{end}"], source[f"bottom_{end}"] = (
            source[f"bottom_{end}"],
            source[f"top_{end}"],
        )
    segment = document["payload_source_map"]["segments"][0]
    start, end = segment["source_span"]["start"]["offset"], segment["source_span"]["end"]["offset"]
    segment["source_span"] = {
        "start": {"offset": len(sequence) - end},
        "end": {"offset": len(sequence) - start},
    }
    segment["orientation"] = "reverse_complement"
    # Every span uses the common duplex frame, which reverses when top and bottom swap.
    for survivor in document["constraints"]["required_survivors"]:
        survivor["precursor_strand"] = "bottom" if survivor["precursor_strand"] == "top" else "top"
        start, end = (
            survivor["source_span"]["start"]["offset"],
            survivor["source_span"]["end"]["offset"],
        )
        survivor["source_span"] = {
            "start": {"offset": len(sequence) - end},
            "end": {"offset": len(sequence) - start},
        }
    return document


def retained_materials(result):
    return {
        tuple(
            sorted(
                (fragment.sequence, fragment.five_prime_end, fragment.three_prime_end)
                for fragment in realization.denatured.fragments
                if fragment.fragment_id in realization.selected.retained_fragment_ids
            )
        )
        for realization in result.realizations
    }


def test_mirrored_partition_preserves_the_same_physical_survivors():
    forward = discover_source_partitions(_request())
    mirrored = SourcePartitionDiscoveryRequest.model_validate_json(json.dumps(mirrored_request()))
    reverse = discover_source_partitions(mirrored)
    assert forward.realizations and reverse.realizations
    assert retained_materials(reverse) == retained_materials(forward)


def test_reversed_source_rejects_wrong_payload_sequence():
    document = mirrored_request()
    document["payload_source_map"]["segments"][0]["orientation"] = "forward"
    with pytest.raises(ValidationError, match="encode a member"):
        SourcePartitionDiscoveryRequest.model_validate_json(json.dumps(document))


def test_reversed_source_requires_the_payload_on_the_retained_bottom_strand():
    document = mirrored_request()
    document["constraints"]["required_survivors"] = tuple(
        item
        for item in document["constraints"]["required_survivors"]
        if item["precursor_strand"] == "top"
    )
    with pytest.raises(ValidationError, match="bottom-strand survivor"):
        SourcePartitionDiscoveryRequest.model_validate_json(json.dumps(document))


def test_reversed_payload_survivor_cannot_use_bottom_five_prime_coordinates():
    document = mirrored_request()
    length = len(document["source"]["top_sequence_5prime"])
    span = document["payload_source_map"]["segments"][0]["source_span"]
    for survivor in document["constraints"]["required_survivors"]:
        if survivor["precursor_strand"] == "bottom":
            survivor["source_span"] = {
                "start": {"offset": length - span["end"]["offset"]},
                "end": {"offset": length - span["start"]["offset"]},
            }
    with pytest.raises(ValidationError, match="bottom-strand survivor"):
        SourcePartitionDiscoveryRequest.model_validate_json(json.dumps(document))
