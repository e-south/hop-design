"""Resumption addresses exact sequence candidates without replaying an earlier prefix."""

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal import iter_basal_program_solutions
from hop_design.kernel.construction.foldback import (
    iter_foldback_program_solutions,
    iter_foldback_programs,
)
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint, FoldbackTarget
from hop_design.models.physical import Strand
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.contract.test_basal_construction_discovery import _pairing_constraints, _request
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
)
from tests.contract.test_foldback_construction_discovery import (
    _request as foldback_request,
)


def test_basal_seek_preserves_original_order_and_recognition_constraints():
    expected = {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX: (
            64,
            "sha256:179883da8756c5309305b7e15667e96636318416777fcc2f65b2f850ea6ad671",
        ),
        ConstructionEndpoint.CLONE_READY_DUPLEX: (
            4,
            "sha256:85ba1bb85c4feb95254f0f5161069576fdd33fb1f8855210a5a2cc589dd24665",
        ),
    }
    for endpoint, (count, digest) in expected.items():
        request = _request(endpoint)
        (unit,) = iter_basal_work_units(request, retained_overhead_nt=4)
        arguments = {
            "payload_sequence": unit.payload_sequence,
            "target": unit.target,
            "endpoint": endpoint,
            "program": unit.program,
        }
        rows = []
        for start in range(0, count, 3):
            rows.extend(
                (item.source_precursor_sequence, item.adapter_sequence)
                for item in iter_basal_program_solutions(
                    **arguments, start=start, stop=min(start + 3, count)
                )
            )
        assert len(rows) == count
        assert sha256_digest(canonical_json_bytes(rows)) == digest


def test_basal_seek_can_recover_a_late_member_without_materializing_prior_candidates(monkeypatch):
    from hop_design.kernel.construction.basal.domains import BasalSequenceDomain

    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        pairing_constraints=_pairing_constraints((BasalPairAllowance.MATCH,) * 20),
    )
    (unit,) = iter_basal_work_units(request, retained_overhead_nt=20)
    original = BasalSequenceDomain.materialize
    calls = 0

    def counted(self, *args):
        nonlocal calls
        calls += 1
        assert calls == 1
        return original(self, *args)

    monkeypatch.setattr(BasalSequenceDomain, "materialize", counted)
    (last,) = iter_basal_program_solutions(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        endpoint=request.endpoint,
        program=unit.program,
        start=4**18 - 1,
        stop=4**18,
    )
    assert last.source_precursor_sequence == "T" * 18 + "AACCCC"
    assert last.adapter_sequence == "TT" + "A" * 18
    assert calls == 1


def test_foldback_seek_keeps_the_correlated_source_order():
    request = foldback_request(_nickase())
    target = FoldbackTarget(
        nick_strand=Strand.TOP, junction_offset_nt=0, loop_length_nt=4, annealing_arm_length_bp=3
    )
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]
    rows = list(
        iter_foldback_program_solutions(
            payload_sequence="GACT", target=target, program=program, start=2, stop=4
        )
    )
    assert [item.source_reference_sequence for item in rows] == ["GACTACATTTCTGT", "GACTACATTTATGT"]


def test_large_partition_uses_an_absolute_address_without_scanning_other_members(monkeypatch):
    from hop_design.kernel.construction.foldback.domains import FoldbackSequenceDomain
    from hop_design.models.construction.sequence_domain import SequenceDomainPartition

    partition = SequenceDomainPartition(part_count=4**9, part_index=4**9 - 1)
    request = foldback_request(_nickase())
    target = FoldbackTarget(
        nick_strand=Strand.TOP, junction_offset_nt=0, loop_length_nt=12, annealing_arm_length_bp=3
    )
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]
    original = FoldbackSequenceDomain.materialize
    calls = 0

    def counted(self, sequence):
        nonlocal calls
        calls += 1
        assert calls == 1
        return original(self, sequence)

    monkeypatch.setattr(FoldbackSequenceDomain, "materialize", counted)
    rows = list(
        iter_foldback_program_solutions(
            payload_sequence="GACT", target=target, program=program, sequence_partition=partition
        )
    )
    assert len(rows) == calls == 1


def test_local_foldback_discovery_seeks_directly_to_the_declared_part(monkeypatch):
    from hop_design.design.construction.foldback import discover_foldback_neighborhood
    from hop_design.kernel.construction.foldback.domains import FoldbackSequenceDomain
    from hop_design.models.construction.sequence_domain import SequenceDomainPartition

    target = FoldbackTarget(
        nick_strand=Strand.TOP, junction_offset_nt=0, loop_length_nt=12, annealing_arm_length_bp=3
    )
    request = foldback_request(_nickase(), target=target)
    request = request.model_copy(
        update={
            "search": request.search.model_copy(
                update={
                    "sequence_partition": SequenceDomainPartition(
                        part_count=4**9, part_index=4**9 - 1
                    )
                }
            )
        }
    )
    original = FoldbackSequenceDomain.materialize
    calls = 0

    def counted(self, sequence):
        nonlocal calls
        calls += 1
        assert calls == 1
        return original(self, sequence)

    monkeypatch.setattr(FoldbackSequenceDomain, "materialize", counted)
    result = discover_foldback_neighborhood(request)
    assert calls == 1
    assert result.neighborhood.disposition.termination_reason.value == "exhausted_domain"
    assert result.neighborhood.payload_compatibility.status.value == "not_computed"
