"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/source_partition/__init__.py

Exposes source-partition discovery and its file-oriented public adapter.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from .discovery import discover_source_partitions
from .public import (
    SourcePartitionDiscovery,
    discover_source_partition,
    load_verified_source_partition,
)

__all__ = [
    "SourcePartitionDiscovery",
    "discover_source_partition",
    "discover_source_partitions",
    "load_verified_source_partition",
]
