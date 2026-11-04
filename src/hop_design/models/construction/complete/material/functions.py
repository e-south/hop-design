"""Project retained route materials onto exact hairpin or duplex product spans."""

from __future__ import annotations

from collections.abc import Iterable

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import MaterialBaseLineage, MolecularStrand

from ..pcr.authority import EndpointStrand, MaterialFunction, MaterialFunctionSpan
from .use import MaterialUse


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _runs(lineage: tuple[MaterialBaseLineage, ...]) -> Iterable[tuple[int, int]]:
    start = 0
    for index in range(1, len(lineage)):
        previous = lineage[index - 1]
        current = lineage[index]
        if (
            current.origin_id != previous.origin_id
            or abs(current.origin_index - previous.origin_index) != 1
        ):
            yield start, index
            start = index
    yield start, len(lineage)


def _material_function_spans(
    use_by_id: dict[str, MaterialUse],
    function_by_use: dict[str, MaterialFunction],
    *,
    top: MolecularStrand,
    bottom: MolecularStrand | None,
) -> tuple[MaterialFunctionSpan, ...]:
    records: list[MaterialFunctionSpan] = []
    for endpoint_strand, product in (
        (EndpointStrand.TOP, top),
        (EndpointStrand.BOTTOM, bottom),
    ):
        if product is None:
            continue
        for start, end in _runs(product.lineage):
            run = product.lineage[start:end]
            function = function_by_use.get(run[0].origin_id)
            material_use = use_by_id.get(run[0].origin_id)
            if function is None or material_use is None:
                raise ValueError("PCR product lineage must resolve to an exact route material.")
            minimum = min(item.origin_index for item in run)
            maximum = max(item.origin_index for item in run) + 1
            orientation = (
                BindingOrientation.SAME_5TO3
                if len(run) == 1 or run[-1].origin_index > run[0].origin_index
                else BindingOrientation.REVERSE_COMPLEMENT_5TO3
            )
            records.append(
                MaterialFunctionSpan(
                    material_use_id=material_use.use_id,
                    material_id=material_use.material_id,
                    function=function,
                    material_span=_span(minimum, maximum),
                    endpoint_strand=endpoint_strand,
                    endpoint_span=_span(start, end),
                    orientation=orientation,
                )
            )
    return tuple(records)


def material_function_spans(
    *,
    material_uses: tuple[MaterialUse, ...],
    top: MolecularStrand,
    bottom: MolecularStrand | None,
) -> tuple[MaterialFunctionSpan, ...]:
    """Map every retained input-material run to its exact endpoint occurrence."""
    return _material_function_spans(
        {material_use.use_id: material_use for material_use in material_uses},
        {
            material_use.use_id: function
            for material_use, function in zip(
                material_uses, tuple(MaterialFunction)[: len(material_uses)], strict=True
            )
        },
        top=top,
        bottom=bottom,
    )


def validate_material_function_spans(
    *,
    records: tuple[MaterialFunctionSpan, ...],
    material_uses: tuple[MaterialUse, ...],
    function_by_use: dict[str, MaterialFunction],
    top: MolecularStrand,
    bottom: MolecularStrand | None,
) -> None:
    """Require material functions to replay their exact endpoint lineage spans."""
    use_by_id = {item.use_id: item for item in material_uses}
    if set(function_by_use.values()) != set(MaterialFunction) or any(
        function_by_use.get(record.material_use_id) is not record.function
        or use_by_id.get(record.material_use_id) is None
        or use_by_id[record.material_use_id].material_id != record.material_id
        for record in records
    ):
        raise ValueError("PCR material-function spans must bind exact route material roles.")
    if records != _material_function_spans(
        use_by_id,
        function_by_use,
        top=top,
        bottom=bottom,
    ):
        raise ValueError("PCR material-function spans must replay exact endpoint lineage.")
