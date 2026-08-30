"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/spaces.py

Previews bounded substrate spaces and owns verified design-set operations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from math import prod
from pathlib import Path
from typing import Literal

from hop_design.catalog.defaults import (
    BASAL_REF,
    DEFAULTS_ANATOMY_SUMMARY,
    DEFAULTS_DISPLAY_NAME,
    DEFAULTS_REF,
    FOLDBACK_REF,
)
from hop_design.design.bundle import VerifiedHopBundle, load_verified_bundle
from hop_design.design.compile import compile_spec, create_catalog_spec
from hop_design.design.space.authority import (
    CANONICAL_DNA_ORDER,
    assignment_text,
    exact_payloads,
    member_design_id,
    molecular_space,
    provisional_design_set,
    seal_design_set,
)
from hop_design.export.bundle import BundleIntegrityError, verify_manifested_bundle_contents
from hop_design.export.publication import publish_directory_create_only
from hop_design.export.space_package import design_set_artifacts, write_space_projections
from hop_design.kernel.bundle_identity import design_set_id, manifest_digest_for_design_set
from hop_design.models.design_space import (
    HairpinDesignMember,
    HairpinDesignSet,
    SubstrateSpacePreview,
    SubstrateSpaceSpec,
)
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac
from hop_design.models.space.scientist import MolecularSubstrateSpace
from hop_design.serialization import canonical_json_bytes, sha256_digest

SCIENTIST_COMPILE_MEMBER_LIMIT = 256


@dataclass(frozen=True)
class VerifiedHairpinDesignSet:
    """A design-set package that passed integrity and member replay checks."""

    path: Path
    design_set: HairpinDesignSet
    spec: MolecularSubstrateSpace
    members: tuple[VerifiedHopBundle, ...]


class SubstrateMemberCompilationError(ValueError):
    """Report one exact assignment that could not compile into a member."""

    def __init__(self, *, ordinal: int, total: int, assignment: str, reason: str) -> None:
        super().__init__(
            f"Compilation stopped at assignment {ordinal} of {total}.\n"
            f"Assignment: {assignment}\n"
            f"Reason: {reason}\n"
            "No output package was committed."
        )


def _authored_payload(spec: SubstrateSpaceSpec) -> str:
    return "".join((segment.fixed or segment.variable or "") for segment in spec.payload)


def preview_space(spec: SubstrateSpaceSpec) -> SubstrateSpacePreview:
    """Symbolically account for a substrate space without enumeration or writes."""
    payload = _authored_payload(spec)
    fixed_positions: list[int] = []
    variable_positions: list[int] = []
    variable_domains: list[tuple[str, ...]] = []
    cursor = 1
    for segment in spec.payload:
        sequence = segment.fixed or segment.variable or ""
        for symbol in sequence:
            if segment.fixed is not None:
                fixed_positions.append(cursor)
            else:
                variable_positions.append(cursor)
                bases = iupac_bases(symbol)
                variable_domains.append(
                    tuple(base for base in CANONICAL_DNA_ORDER if base in bases)
                )
            cursor += 1
    cardinality = prod(len(domain) for domain in variable_domains)
    state: Literal["ready", "blocked", "invalid"]
    if cardinality > SCIENTIST_COMPILE_MEMBER_LIMIT:
        state = "blocked"
        message = (
            f"This valid specification defines {cardinality} exact assignments. "
            f"Compilation supports up to {SCIENTIST_COMPILE_MEMBER_LIMIT} designs "
            "in this release."
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
        compilation_limit=SCIENTIST_COMPILE_MEMBER_LIMIT,
        message=message,
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
        normalized_space = molecular_space(spec)
        canonical_spec = canonical_json_bytes(normalized_space)
        spec_digest = sha256_digest(canonical_spec)
        (bundle_root / "spec.json").write_bytes(canonical_spec)

        records: list[HairpinDesignMember] = []
        encoding_ordinals: dict[str, int] = {}
        canonical_records: dict[int, HairpinDesignMember] = {}
        for ordinal, (assignments, exact_payload) in enumerate(
            exact_payloads(normalized_space), start=1
        ):
            design_id = member_design_id(
                spec_digest=spec_digest,
                assignments=assignments,
            )
            try:
                compilation = compile_spec(
                    create_catalog_spec(sequence=exact_payload, design_id=design_id)
                )
            except ValueError as exc:
                raise SubstrateMemberCompilationError(
                    ordinal=ordinal,
                    total=preview.theoretical_cardinality,
                    assignment=assignment_text(spec, assignments),
                    reason=str(exc),
                ) from exc
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

        provisional = provisional_design_set(
            spec=spec,
            spec_digest=spec_digest,
            members=tuple(records),
            artifacts=design_set_artifacts(bundle_root),
        )
        design_set = seal_design_set(provisional)
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
            defaults_display_name=DEFAULTS_DISPLAY_NAME,
            defaults_anatomy_summary=DEFAULTS_ANATOMY_SUMMARY,
            foldback_ref=FOLDBACK_REF,
            basal_ref=BASAL_REF,
        )
        publish_directory_create_only(staging, output)
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
    expected_payloads = exact_payloads(spec)
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
