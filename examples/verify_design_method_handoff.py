"""Write, verify, and compare one matched design and method bundle pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hop_design as hop
import hop_design.methods as methods


def main() -> None:
    """Materialize two sibling bundles and verify their caller-owned digest relation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    example_root = Path(__file__).resolve().parent
    design_spec = hop.load_spec(example_root / "linear-source-matched-design.yaml")
    method_request = methods.LinearSourceMultinickHairpinPcrRequest.model_validate_json(
        (example_root / "linear-source-method.json").read_text(encoding="utf-8")
    )
    design_compilation = hop.compile(design_spec)
    method_compilation = methods.compile_linear_source_method_bundle(method_request)

    args.out.mkdir(parents=True, exist_ok=False)
    design_path = design_compilation.write(args.out / "design")
    method_path = method_compilation.write(args.out / "method")
    verified_design = hop.load_verified_bundle(design_path)
    verified_method = methods.load_verified_method_bundle(method_path)

    design_digest = verified_design.plan.hairpin_encoding_insert.sequence_digest
    method_bundle_digest = verified_method.bundle.hairpin_encoding_digest
    product_projection_digest = (
        verified_method.plan.restriction_digest_product.hairpin_encoding_projection.sequence_digest
    )
    if not design_digest == method_bundle_digest == product_projection_digest:
        raise ValueError("Verified design and method bundles encode different hairpins.")

    print(
        json.dumps(
            {
                "design_bundle_verified": True,
                "method_bundle_verified": True,
                "design_digest": design_digest,
                "method_bundle_digest": method_bundle_digest,
                "product_projection_digest": product_projection_digest,
                "design_bundle_id": verified_design.bundle.bundle_id,
                "method_bundle_id": verified_method.bundle.bundle_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
