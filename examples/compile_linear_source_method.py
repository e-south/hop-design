"""Compile, write, and verify the public linear-source method example."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hop_design.methods as methods


def main() -> None:
    """Resolve one exact method request and report its verified product."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--request",
        type=Path,
        default=Path(__file__).with_name("linear-source-method.json"),
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    request = methods.LinearSourceMultinickHairpinPcrRequest.model_validate_json(
        args.request.read_text(encoding="utf-8")
    )
    compilation = methods.compile_linear_source_method_bundle(request)
    compilation.write(args.out)
    verified = methods.load_verified_method_bundle(args.out)
    product = verified.plan.restriction_digest_product

    assert verified.bundle.hairpin_encoding_digest == (
        product.hairpin_encoding_projection.sequence_digest
    )
    print(
        json.dumps(
            {
                "method_kind": verified.plan.method_kind,
                "bundle_id": verified.bundle.bundle_id,
                "product_state": product.state_id,
                "hairpin_encoding_digest": verified.bundle.hairpin_encoding_digest,
                "cohesive_ends": [
                    {
                        "product_end": end.product_end,
                        "polarity": end.overhang_end,
                        "sequence": end.sequence,
                    }
                    for end in product.cohesive_ends
                ],
                "destination_readiness": product.destination_readiness,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
