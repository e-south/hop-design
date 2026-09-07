"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/routes.py

Lists and filters exact routes from verified construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any

import typer

from .common import load_receipt, navigation_content

_STATUS_VALUES = {"accepted", "rejected", "truncated", "all"}
_GROUP_VALUES = {"geometry", "product", "none"}
_SORT_FIELDS = {
    "canonical": "ordinal",
    "retained-overhead": "retained_non_payload_nt",
    "cleavage-enzyme-count": "enzyme_count",
    "auxiliary-count": "auxiliary_material_count",
    "source-length": "source_material_nt",
}


def _validate_list_options(
    *,
    status: str,
    group_by: str,
    group: str | None,
    sort: str,
    exact: bool,
    relaxed: bool,
    limit: int,
    has_enzyme_filter: bool,
) -> None:
    if status not in _STATUS_VALUES:
        raise typer.BadParameter(
            f"Unknown status {status!r}; use accepted, rejected, truncated, or all.",
            param_hint="--status",
        )
    if group_by not in _GROUP_VALUES:
        raise typer.BadParameter(
            f"Unknown grouping {group_by!r}; use geometry, product, or none.",
            param_hint="--group-by",
        )
    if sort not in _SORT_FIELDS:
        raise typer.BadParameter(
            f"Unknown sort {sort!r}; use {', '.join(_SORT_FIELDS)}.",
            param_hint="--sort",
        )
    if exact and relaxed:
        raise typer.BadParameter(
            "--exact and --relaxed are mutually exclusive.",
            param_hint="--exact/--relaxed",
        )
    if limit < 1 or limit > 1_000:
        raise typer.BadParameter("--limit must be between 1 and 1,000.", param_hint="--limit")
    if group is not None and group_by == "none":
        raise typer.BadParameter(
            "--group requires geometry or product grouping.",
            param_hint="--group",
        )
    if status != "accepted" and group_by != "none":
        raise typer.BadParameter(
            "Rejected, truncated, and mixed listings require --group-by none.",
            param_hint="--group-by",
        )
    if (exact or relaxed) and status not in {"accepted", "all"}:
        raise typer.BadParameter(
            "Geometry-relaxation filters apply only to accepted routes.",
            param_hint="--exact/--relaxed",
        )
    if sort != "canonical" and status != "accepted":
        raise typer.BadParameter(
            "Non-canonical route sorts apply only to accepted routes.",
            param_hint="--sort",
        )
    if has_enzyme_filter and status != "accepted":
        raise typer.BadParameter(
            "Enzyme filters apply only to accepted routes.",
            param_hint="--enzyme",
        )


def _group_field(group_by: str) -> str | None:
    if group_by == "geometry":
        return "achieved_geometry_group_key"
    if group_by == "product":
        return "final_product_group_key"
    return None


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    status: str,
    group_by: str,
    group: str | None,
    enzymes: tuple[str, ...],
    exact: bool,
    relaxed: bool,
) -> list[dict[str, Any]]:
    selected = rows if status == "all" else [row for row in rows if row["status"] == status]
    group_field = _group_field(group_by)
    if group is not None:
        assert group_field is not None
        selected = [row for row in selected if row.get(group_field) == group]
    if enzymes:
        required = set(enzymes)
        selected = [row for row in selected if required <= set(row.get("enzyme_ids", ()))]
    if exact:
        selected = [row for row in selected if row.get("exact_geometry") is True]
    if relaxed:
        selected = [row for row in selected if row.get("exact_geometry") is False]
    return selected


def _sort_rows(
    rows: list[dict[str, Any]],
    *,
    sort: str,
    descending: bool,
) -> list[dict[str, Any]]:
    if sort == "canonical":
        return sorted(rows, key=lambda row: row["ordinal"], reverse=descending)
    field = _SORT_FIELDS[sort]
    if descending:
        return sorted(rows, key=lambda row: (-int(row[field]), row["ordinal"]))
    return sorted(rows, key=lambda row: (int(row[field]), row["ordinal"]))


def _foldback_text(geometry: dict[str, Any]) -> str:
    return (
        f"nick {geometry['junction_offset_nt']} nt into arm; "
        f"loop {geometry['loop_length_nt']} nt; "
        f"annealing arm {geometry['annealing_arm_length_bp']} bp; "
        f"nick strand {geometry['nick_strand']}"
    )


def _basal_text(geometry: dict[str, Any] | None) -> str:
    if geometry is None:
        return "not required for this endpoint"
    pairing = (
        "/".join(item["allowed_class"] for item in geometry.get("pairing_constraints", ()))
        or "none"
    )
    return (
        f"nick offset {geometry['nick_offset_nt']} nt; "
        f"nick strand {geometry['nick_strand']}; pairing {pairing}"
    )


def _route_line(row: dict[str, Any]) -> str:
    if row["status"] != "accepted":
        basis = row.get("rejection_reason") or row.get("truncation_reason") or "unspecified"
        return f"  {row['ordinal']:>4}  {row['status']} · {basis}"
    resolution = "exact" if row["exact_geometry"] else "relaxed"
    enzymes = ",".join(row["enzyme_ids"]) or "none"
    return (
        f"  {row['ordinal']:>4}  {resolution} · "
        f"{row['retained_non_payload_nt']} retained non-payload nt · "
        f"cleavage_enzymes={enzymes} · auxiliaries={row['auxiliary_material_count']} · "
        f"{row['materialized_realization_id']}"
    )


def _render_list(
    rows: list[dict[str, Any]],
    *,
    group_by: str,
    limit: int,
) -> None:
    visible = rows[:limit]
    field = _group_field(group_by)
    if field is None:
        for row in visible:
            typer.echo(_route_line(row))
    else:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in visible:
            groups[str(row[field])].append(row)
        for key, members in groups.items():
            typer.echo(f"Group: {key} · {len(members)} displayed route(s)")
            if group_by == "geometry":
                typer.echo(f"  Foldback: {_foldback_text(members[0]['foldback_geometry'])}")
                typer.echo(f"  Basal: {_basal_text(members[0]['basal_geometry'])}")
            for row in members:
                typer.echo(_route_line(row))
    typer.echo(f"Showing {len(visible)} of {len(rows)} matched routes.")
    if len(visible) != len(rows):
        typer.echo("Display limiting does not change the verified search status or accounting.")
    typer.echo("Ordinal is canonical replay order, not rank.")


def construction_list_command(
    bundle_path: Annotated[
        Path,
        typer.Argument(help="Verified HOP construction bundle directory."),
    ],
    status: Annotated[
        str,
        typer.Option("--status", help="accepted, rejected, truncated, or all."),
    ] = "accepted",
    group_by: Annotated[
        str,
        typer.Option("--group-by", help="geometry, product, or none."),
    ] = "geometry",
    group: Annotated[
        str | None,
        typer.Option("--group", help="Exact group key to retain."),
    ] = None,
    enzyme: Annotated[
        list[str] | None,
        typer.Option(
            "--enzyme",
            help="Require a cleavage-program enzyme ID; repeat to require several.",
        ),
    ] = None,
    exact: Annotated[
        bool,
        typer.Option("--exact", help="Retain only zero-relaxation accepted routes."),
    ] = False,
    relaxed: Annotated[
        bool,
        typer.Option("--relaxed", help="Retain only relaxed accepted routes."),
    ] = False,
    sort: Annotated[
        str,
        typer.Option(
            "--sort",
            help=(
                "canonical, retained-overhead, cleavage-enzyme-count, auxiliary-count, "
                "or source-length."
            ),
        ),
    ] = "canonical",
    descending: Annotated[
        bool,
        typer.Option("--descending", help="Reverse the explicitly selected sort dimension."),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum displayed rows; scientific accounting is intact."),
    ] = 25,
) -> None:
    """List exact dispositions without ranking or changing result authority."""
    requested_enzymes = tuple(enzyme or ())
    _validate_list_options(
        status=status,
        group_by=group_by,
        group=group,
        sort=sort,
        exact=exact,
        relaxed=relaxed,
        limit=limit,
        has_enzyme_filter=bool(requested_enzymes),
    )
    receipt = load_receipt(bundle_path)
    content = navigation_content(receipt)
    known_enzymes = {
        enzyme_id for row in content["rows"] for enzyme_id in row.get("enzyme_ids", ())
    }
    unknown_enzymes = tuple(sorted(set(requested_enzymes) - known_enzymes))
    if unknown_enzymes:
        raise typer.BadParameter(
            f"Unknown route enzyme(s): {', '.join(unknown_enzymes)}",
            param_hint="--enzyme",
        )
    group_field = _group_field(group_by)
    if group is not None:
        group_collection = (
            content["geometry_groups"]
            if group_by == "geometry"
            else content["final_product_groups"]
        )
        if group not in {item["group_key"] for item in group_collection}:
            label = "achieved-geometry" if group_by == "geometry" else "final-product"
            raise typer.BadParameter(f"Unknown {label} group: {group}", param_hint="--group")
    rows = _filter_rows(
        content["rows"],
        status=status,
        group_by=group_by,
        group=group,
        enzymes=requested_enzymes,
        exact=exact,
        relaxed=relaxed,
    )
    rows = _sort_rows(rows, sort=sort, descending=descending)
    order = "descending" if descending else "ascending"
    typer.echo(f"Query: status={status} · group_by={group_by} · sort={sort} · order={order}")
    if group_field is not None and not rows:
        typer.echo("No accepted geometry or product groups matched the explicit filters.")
    _render_list(rows, group_by=group_by, limit=limit)


__all__ = ["construction_list_command"]
