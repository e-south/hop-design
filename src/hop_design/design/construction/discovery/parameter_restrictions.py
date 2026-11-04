"""Compile selected coordinates into narrower requests; joint geometry stays joint."""

from copy import deepcopy
from itertools import islice
from typing import Any

from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.variants.parameters import ParameterSelection
from hop_design.models.enzymes import EnzymeProvisioningPolicy, EnzymeRole
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..overhead import iter_foldback_geometries

_FOLDBACK = {
    "foldback_arm_bp",
    "join_offset_nt",
    "self_paired_arm_bp",
    "loop_nt",
    "loop_word",
    "loop_side_paired_bp",
}


def _foldbacks(
    product: dict[str, Any], selections: dict[str, ParameterSelection]
) -> list[dict[str, Any]]:
    selected = {key: s for key, s in selections.items() if key in _FOLDBACK}
    if not selected:
        return [product]
    source = ProductRequest.model_validate_json(canonical_json_bytes(product))
    domain = source.foldback.geometry
    word = selected.get("loop_word")
    if word and word.values:
        words = tuple(
            w
            for w in word.values
            if isinstance(w, str)
            and (domain.loop_sequences is None or w in domain.loop_sequences)
            and len(w) >= domain.minimum_loop_length_nt
            and (not domain.loop_lengths_nt or len(w) in domain.loop_lengths_nt)
        )
        if not words:
            return []
        domain = domain.model_copy(update={"loop_sequences": words})
    maximum = source.foldback.search.max_retained_overhead_nt
    # Avoid an unbounded planning traversal even when local search has a small node cap.
    if maximum > 1024:
        raise ValueError("Parameter-targeted planning requires retained overhead <= 1024 nt.")
    result = []
    for ordinal, target in enumerate(
        islice(iter_foldback_geometries(domain, maximum=maximum), 100_001)
    ):
        if ordinal == 100_000:
            raise ValueError("Parameter planning exceeds 100000 geometries; narrow the domain.")
        values = {
            "foldback_arm_bp": target.annealing_arm_length_bp,
            "loop_side_paired_bp": target.annealing_arm_length_bp,
            "join_offset_nt": target.junction_offset_nt,
            "self_paired_arm_bp": target.annealing_arm_length_bp - target.junction_offset_nt,
            "loop_nt": target.loop_length_nt,
            "loop_word": target.loop_sequence,
        }
        if not all(s.accepts(values[key]) for key, s in selected.items()):
            continue
        value = deepcopy(product)
        value["foldback"]["geometry"].update(
            annealing_arm_lengths_bp=[target.annealing_arm_length_bp],
            junction_offsets_nt=[target.junction_offset_nt],
            loop_lengths_nt=[target.loop_length_nt],
            loop_sequences=[target.loop_sequence] if target.loop_sequence is not None else None,
        )
        result.append(value)
        if len(result) > 256:
            raise ValueError(
                "Parameter-targeted planning exceeds 256 branches; narrow the selection."
            )
    return result


def _narrow(product: dict[str, Any], selections: dict[str, ParameterSelection]) -> bool:
    for side in ("left", "right"):
        end = (product.get("ends") or {}).get(side)
        for suffix, field in (
            ("gap", "payload_end_offset_bp"),
            ("end_word", "cohesive_end_sequence"),
            ("end_polarity", "overhang_end"),
        ):
            if (selection := selections.get(f"{side}_{suffix}")) and (
                end is None or not selection.accepts(end[field])
            ):
                return False
    for role, key in (("foldback", "foldback_strand"), ("basal", "basal_strand")):
        if selection := selections.get(key):
            job = product.get(role)
            if job is None:
                return False
            geometry = job["geometry"]
            values = [
                v
                for v in ("top", "bottom")
                if selection.accepts(v) and geometry["nick_strand"] in (v, "any")
            ]
            if not values:
                return False
            geometry["nick_strand"] = values[0] if len(values) == 1 else "any"
    if selection := selections.get("basal_nick_offset_nt"):
        if product.get("basal") is None:
            return False
        geometry = product["basal"]["geometry"]
        geometry["nick_offsets_nt"] = [
            v for v in geometry["nick_offsets_nt"] if selection.accepts(v)
        ]
        if not geometry["nick_offsets_nt"]:
            return False
    selection = selections.get("adapter_annealing_min_nt")
    if selection and (
        not product.get("basal")
        or not selection.accepts(product["basal"]["geometry"]["minimum_adapter_annealing_nt"])
    ):
        return False
    return _methods(product, selections) and _bases(product, selections)


def _methods(product: dict[str, Any], selections: dict[str, ParameterSelection]) -> bool:
    source = ProductRequest.model_validate_json(canonical_json_bytes(product))
    for role, purpose in (
        ("foldback", EnzymeRole.FOLDBACK_NICK),
        ("basal", EnzymeRole.BASAL_NICK),
        ("release", EnzymeRole.END_GENERATION),
    ):
        if selection := selections.get(f"{role}_method"):
            job = getattr(source, role)
            if job is None:
                return False
            policy = EnzymeProvisioningPolicy(
                catalog=source.enzyme_catalog, **job.enzymes.model_dump()
            )
            ids = [
                e.enzyme_id
                for e in source.enzyme_catalog.enzymes
                if selection.accepts(e.enzyme_id) and policy.permits(e.enzyme_id, role=purpose)
            ]
            if not ids:
                return False
            permissions = product[role]["enzymes"]
            permissions["role_restrictions"] = [
                r for r in permissions["role_restrictions"] if r["role"] != purpose.value
            ] + [{"role": purpose.value, "allowed_enzyme_ids": ids}]
    return True


def _bases(product: dict[str, Any], selections: dict[str, ParameterSelection]) -> bool:
    for key, selection in selections.items():
        if not key.startswith(("basal_source_base_", "basal_adapter_base_", "basal_pair_class_")):
            continue
        if product.get("basal") is None:
            return False
        pairs = product["basal"]["geometry"]["pairing_constraints"]
        index = int(key.rsplit("_", 1)[1])
        if index >= len(pairs):
            return False
        pair = pairs[index]
        if "pair_class" in key:
            classes = [
                c
                for c in ("match", "wobble", "mismatch")
                if selection.accepts(c) and pair["allowed_class"] in (c, "any")
            ]
            if not classes:
                return False
            if len(classes) == 1:
                pair["allowed_class"] = classes[0]
            # Multiple classes retain the original generator; complete admission
            # enforces the exact disjunction rather than relaxing it to 'any'.
        else:
            field = "allowed_source_bases" if "source_base" in key else "allowed_adapter_bases"
            pair[field] = [base for base in pair.get(field, "ACGT") if selection.accepts(base)]
            if not pair[field]:
                return False
    return True


def restrict_parameter_branches(
    branches: list[dict[str, Any]], parameters: tuple[ParameterSelection, ...], stage: str
) -> list[dict[str, Any]]:
    selections = {selection.key: selection for selection in parameters}
    result = []
    for branch in branches:
        base = deepcopy(branch["request"])
        if not _narrow(base, selections):
            continue
        for product in _foldbacks(base, selections):
            ProductRequest.model_validate_json(canonical_json_bytes(product))
            value = {
                **branch,
                "request": product,
                "parameter_constraints": [
                    p.model_dump(mode="json", exclude_none=True) for p in parameters
                ],
                "parameter_stage": stage,
            }
            value["branch_id"] = sha256_digest(
                canonical_json_bytes(
                    {
                        "request": product,
                        "parameters": value["parameter_constraints"],
                        "stage": stage,
                    }
                )
            )
            result.append(value)
            if len(result) > 256:
                raise ValueError(
                    "Parameter-targeted planning exceeds 256 branches; narrow the selection."
                )
    return result
