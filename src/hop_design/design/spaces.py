"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/spaces.py

Previews bounded substrate spaces and owns verified design-set operations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from itertools import product
from math import prod
from pathlib import Path
from typing import Literal, cast

from hop_design.catalog.defaults import DEFAULTS_REF
from hop_design.design.bundle import VerifiedHopBundle, load_verified_bundle
from hop_design.design.compile import compile_spec, create_catalog_spec
from hop_design.export.bundle import BundleIntegrityError, verify_manifested_bundle_contents
from hop_design.export.space_package import design_set_artifacts, write_space_projections
from hop_design.kernel.bundle_identity import design_set_id, manifest_digest_for_design_set
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.design_space import (
    HairpinDesignMember,
    HairpinDesignSet,
    MolecularSubstrateSpace,
    SubstrateSpacePreview,
    SubstrateSpaceSpec,
    VariableAssignment,
)
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest

_BASE_ORDER = ("A", "C", "G", "T")


@dataclass(frozen=True)
class VerifiedHairpinDesignSet:
    """A design-set package that passed integrity and member replay checks."""

    path: Path
    design_set: HairpinDesignSet
    spec: MolecularSubstrateSpace
    members: tuple[VerifiedHopBundle, ...]


def _authored_payload(spec: SubstrateSpaceSpec) -> str:
    return "".join((segment.fixed or segment.variable or "") for segment in spec.payload.segments)


def preview_space(spec: SubstrateSpaceSpec) -> SubstrateSpacePreview:
    """Symbolically account for a substrate space without enumeration or writes."""
    payload = _authored_payload(spec)
    fixed_positions: list[int] = []
    variable_positions: list[int] = []
    variable_domains: list[tuple[str, ...]] = []
    cursor = 1
    for segment in spec.payload.segments:
        sequence = segment.fixed or segment.variable or ""
        for symbol in sequence:
            if segment.fixed is not None:
                fixed_positions.append(cursor)
            else:
                variable_positions.append(cursor)
                bases = iupac_bases(symbol)
                variable_domains.append(tuple(base for base in _BASE_ORDER if base in bases))
            cursor += 1
    cardinality = prod(len(domain) for domain in variable_domains)
    state: Literal["ready", "blocked", "invalid"]
    if spec.hairpin.defaults_ref != DEFAULTS_REF:
        state = "invalid"
        message = (
            f"Unknown defaults reference {spec.hairpin.defaults_ref!r}; "
            f"locked catalog supports {DEFAULTS_REF!r}."
        )
    elif cardinality > spec.enumeration.max_members:
        state = "blocked"
        message = (
            f"This valid specification defines {cardinality} variants, above "
            f"max_members={spec.enumeration.max_members}."
        )
    else:
        state = "ready"
        message = None
    length = len(payload)
    return SubstrateSpacePreview(
        state=state,
        name=spec.name,
        authored_payload=payload,
        derived_paired_payload=reverse_complement_iupac(payload),
        fixed_positions=tuple(fixed_positions),
        variable_positions=tuple(variable_positions),
        variable_domains=tuple(variable_domains),
        paired_positions=tuple(
            (position, length - position + 1) for position in range(1, length + 1)
        ),
        theoretical_cardinality=cardinality,
        max_members=spec.enumeration.max_members,
        message=message,
    )


def _molecular_space(spec: SubstrateSpaceSpec) -> MolecularSubstrateSpace:
    payload_domains: list[tuple[Literal["A", "C", "G", "T"], ...]] = []
    for segment in spec.payload.segments:
        sequence = segment.fixed or segment.variable or ""
        for symbol in sequence:
            bases = iupac_bases(symbol)
            payload_domains.append(
                tuple(
                    cast(Literal["A", "C", "G", "T"], base) for base in _BASE_ORDER if base in bases
                )
            )
    return MolecularSubstrateSpace(
        payload_domains=tuple(payload_domains),
        defaults_ref=spec.hairpin.defaults_ref,
    )


def _exact_payloads(
    molecular_space: MolecularSubstrateSpace,
) -> tuple[tuple[tuple[VariableAssignment, ...], str], ...]:
    variable_positions = tuple(
        position
        for position, domain in enumerate(molecular_space.payload_domains, start=1)
        if len(domain) > 1
    )
    variable_domains = tuple(
        domain for domain in molecular_space.payload_domains if len(domain) > 1
    )
    template = [domain[0] for domain in molecular_space.payload_domains]
    results: list[tuple[tuple[VariableAssignment, ...], str]] = []
    for bases in product(*variable_domains):
        exact = template.copy()
        assignments = tuple(
            VariableAssignment(
                position=position,
                base=cast(Literal["A", "C", "G", "T"], base),
            )
            for position, base in zip(variable_positions, bases, strict=True)
        )
        for assignment in assignments:
            exact[assignment.position - 1] = assignment.base
        results.append((assignments, "".join(exact)))
    return tuple(results)


def _member_design_id(*, spec_digest: str, assignments: tuple[VariableAssignment, ...]) -> str:
    assignment_digest = sha256_digest(
        canonical_json_bytes([assignment.model_dump(mode="json") for assignment in assignments])
    )
    return (
        f"space-{spec_digest.removeprefix('sha256:')[:12]}-"
        f"member-{assignment_digest.removeprefix('sha256:')[:12]}"
    )


def _provisional_design_set(
    *,
    spec: SubstrateSpaceSpec,
    spec_digest: str,
    members: tuple[HairpinDesignMember, ...],
    artifacts: tuple[ArtifactManifestEntry, ...],
) -> HairpinDesignSet:
    unique_designs = sum(member.disposition == "canonical" for member in members)
    duplicate_count = len(members) - unique_designs
    return HairpinDesignSet(
        design_set_id="hop:design-set/pending/pending",
        spec_digest=spec_digest,
        defaults_ref=spec.hairpin.defaults_ref,
        theoretical_cardinality=len(members),
        enumerated_assignments=len(members),
        unique_designs=unique_designs,
        duplicate_count=duplicate_count,
        members=members,
        artifacts=artifacts,
        manifest_digest=f"sha256:{'0' * 64}",
    )


def _seal_design_set(design_set: HairpinDesignSet) -> HairpinDesignSet:
    digest = manifest_digest_for_design_set(design_set)
    return design_set.model_copy(
        update={
            "design_set_id": design_set_id(manifest_digest=digest),
            "manifest_digest": digest,
        }
    )


def compile_space(
    spec: SubstrateSpaceSpec,
    *,
    destination: str | Path,
) -> VerifiedHairpinDesignSet:
    """Compile one complete design set into a new destination."""
    preview = preview_space(spec)
    if preview.state != "ready":
        raise ValueError(preview.message or f"Substrate-space preview is {preview.state}.")
    output = Path(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace existing design-set path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        bundle_root = staging / "bundle"
        members_root = bundle_root / "members"
        members_root.mkdir(parents=True)
        molecular_space = _molecular_space(spec)
        canonical_spec = canonical_json_bytes(molecular_space)
        spec_digest = sha256_digest(canonical_spec)
        (bundle_root / "spec.json").write_bytes(canonical_spec)

        records: list[HairpinDesignMember] = []
        encoding_ordinals: dict[str, int] = {}
        canonical_records: dict[int, HairpinDesignMember] = {}
        for ordinal, (assignments, exact_payload) in enumerate(
            _exact_payloads(molecular_space), start=1
        ):
            design_id = _member_design_id(
                spec_digest=spec_digest,
                assignments=assignments,
            )
            compilation = compile_spec(
                create_catalog_spec(sequence=exact_payload, design_id=design_id)
            )
            encoding_digest = compilation.plan.hairpin_encoding_insert.sequence_digest
            canonical_ordinal = encoding_ordinals.get(encoding_digest)
            if canonical_ordinal is None:
                member_path = f"members/{design_id}"
                compilation.write(bundle_root / member_path)
                record = HairpinDesignMember(
                    canonical_ordinal=ordinal,
                    variable_assignment=assignments,
                    exact_payload=exact_payload,
                    derived_paired_payload=compilation.plan.paired_payload_sequence,
                    exact_hairpin_length=len(compilation.plan.hairpin_encoding_insert.sequence),
                    exact_encoding_digest=encoding_digest,
                    member_bundle_id=compilation.bundle.bundle_id,
                    member_bundle_path=member_path,
                    disposition="canonical",
                )
                encoding_ordinals[encoding_digest] = ordinal
                canonical_records[ordinal] = record
            else:
                canonical = canonical_records[canonical_ordinal]
                record = HairpinDesignMember(
                    canonical_ordinal=ordinal,
                    variable_assignment=assignments,
                    exact_payload=exact_payload,
                    derived_paired_payload=compilation.plan.paired_payload_sequence,
                    exact_hairpin_length=canonical.exact_hairpin_length,
                    exact_encoding_digest=encoding_digest,
                    member_bundle_id=canonical.member_bundle_id,
                    member_bundle_path=canonical.member_bundle_path,
                    disposition="duplicate",
                    canonical_member_ordinal=canonical_ordinal,
                )
            records.append(record)

        provisional = _provisional_design_set(
            spec=spec,
            spec_digest=spec_digest,
            members=tuple(records),
            artifacts=design_set_artifacts(bundle_root),
        )
        design_set = _seal_design_set(provisional)
        (bundle_root / "manifest.json").write_bytes(canonical_json_bytes(design_set))
        staged_verified = load_verified_design_set(bundle_root)
        write_space_projections(
            staging,
            spec=spec,
            design_set=staged_verified.design_set,
            member_encodings={
                member.bundle.bundle_id: (
                    member.plan.design_id,
                    member.plan.hairpin_encoding_insert.sequence,
                )
                for member in staged_verified.members
            },
            verified_member_count=len(staged_verified.members),
        )
        os.replace(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return load_verified_design_set(output / "bundle")


def load_verified_design_set(bundle_path: str | Path) -> VerifiedHairpinDesignSet:
    """Load and semantically verify one design-set authority."""
    root = Path(bundle_path)
    design_set, artifacts = verify_manifested_bundle_contents(
        root,
        manifest_name="manifest.json",
        manifest_model=HairpinDesignSet,
    )
    spec_content = artifacts.get("spec.json")
    if spec_content is None:
        raise BundleIntegrityError("Design-set authority omits spec.json.")
    try:
        spec = MolecularSubstrateSpace.model_validate_json(spec_content)
    except Exception as exc:
        raise BundleIntegrityError(f"Design-set spec.json is invalid: {exc}") from exc
    if sha256_digest(spec_content) != design_set.spec_digest:
        raise BundleIntegrityError("Design-set spec digest mismatch.")
    digest = manifest_digest_for_design_set(design_set)
    if digest != design_set.manifest_digest:
        raise BundleIntegrityError("Design-set manifest digest mismatch.")
    if design_set.design_set_id != design_set_id(manifest_digest=digest):
        raise BundleIntegrityError("Design-set identifier does not match its manifest digest.")
    if spec.defaults_ref != DEFAULTS_REF:
        raise BundleIntegrityError("Canonical design-set spec names an unknown defaults reference.")
    expected_payloads = _exact_payloads(spec)
    if len(expected_payloads) != len(design_set.members):
        raise BundleIntegrityError("Design-set members do not match symbolic space accounting.")

    verified_by_path: dict[str, VerifiedHopBundle] = {}
    for record, (assignments, payload) in zip(design_set.members, expected_payloads, strict=True):
        if record.variable_assignment != assignments or record.exact_payload != payload:
            raise BundleIntegrityError(
                "Design-set member order disagrees with canonical expansion."
            )
        if record.derived_paired_payload != reverse_complement_iupac(payload):
            raise BundleIntegrityError(
                "Design-set member paired payload is not the derived complement."
            )
        member = verified_by_path.get(record.member_bundle_path)
        if member is None:
            member = load_verified_bundle(root / record.member_bundle_path)
            verified_by_path[record.member_bundle_path] = member
        if (
            member.bundle.bundle_id != record.member_bundle_id
            or member.plan.payload_sequence != record.exact_payload
            or member.plan.paired_payload_sequence != record.derived_paired_payload
            or member.plan.hairpin_encoding_insert.sequence_digest != record.exact_encoding_digest
            or len(member.plan.hairpin_encoding_insert.sequence) != record.exact_hairpin_length
        ):
            raise BundleIntegrityError(
                "Design-set member record disagrees with its verified bundle."
            )
    canonical_members = tuple(
        verified_by_path[record.member_bundle_path]
        for record in design_set.members
        if record.disposition == "canonical"
    )
    return VerifiedHairpinDesignSet(
        path=root,
        design_set=design_set,
        spec=spec,
        members=canonical_members,
    )


__all__ = [
    "VerifiedHairpinDesignSet",
    "compile_space",
    "load_verified_design_set",
    "preview_space",
]
