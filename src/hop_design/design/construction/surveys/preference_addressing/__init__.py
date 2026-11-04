"""Inverse addressing for bounded reference hints; ordinary compilation stays authoritative."""

from .resolve import addresses_for_preparation
from .types import MaterialSignature, PreferenceOutOfScope, PreparationAddress, material_signature

__all__ = [
    "MaterialSignature",
    "PreferenceOutOfScope",
    "PreparationAddress",
    "addresses_for_preparation",
    "material_signature",
]
