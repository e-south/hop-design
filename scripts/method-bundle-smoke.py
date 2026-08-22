#!/usr/bin/env python3
"""Exercise one public method request through an installed HOP distribution."""

from __future__ import annotations

import argparse
from pathlib import Path

import hop_design as hop


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    request = hop.LinearSourceMultinickHairpinPcrRequest.model_validate_json(
        args.request.read_bytes()
    )
    compilation = hop.compile_linear_source_method_bundle(request)
    if args.out is not None:
        output = compilation.write(args.out)
        hop.verify_method_bundle(output)
    print(compilation.bundle.manifest_digest)


if __name__ == "__main__":
    main()
