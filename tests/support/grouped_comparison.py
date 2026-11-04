"""Public synthetic requests shared by comparison journey tests."""

import json

from hop_design import construction
from tests.integration.test_comparison_assessment import comparison
from tests.integration.test_scaffold_discovery import method_request


def create_method_pool(root):
    path = method_request(root)
    discovery = json.loads(path.read_bytes())
    discovery["product"]["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4]
    discovery["preparation_changes"]["release_enzyme_ids"] = [
        "example:enzyme/bsai-hfv2@1",
        "example:enzyme/bsmbi-v2@1",
    ]
    path.write_text(json.dumps(discovery))
    return discovery, construction.discover_scaffolds(path).write(root / "pool")


def grouped_brief(tmp_path, discovery):
    members = [
        {
            "name": f"loop{loop}-{method}",
            "dimensions": {"loop_nt": loop},
            "release_enzyme_id": f"example:enzyme/{enzyme}@1",
        }
        for loop in (3, 4)
        for method, enzyme in (("bsai", "bsai-hfv2"), ("bsmbi", "bsmbi-v2"))
    ]
    path = comparison(tmp_path, discovery, stage="endpoint", members=members)
    request = json.loads(path.read_bytes())
    request.update(
        {
            "schema": "hop.comparison-brief/v2",
            "purpose": "grouped_substrates",
            "groups": [
                {
                    "name": f"loop{loop}",
                    "members": [f"loop{loop}-bsai", f"loop{loop}-bsmbi"],
                    "product_relationship": "identical",
                }
                for loop in (3, 4)
            ],
            "between_groups": "distinct",
        }
    )
    path.write_text(json.dumps(request))
    return path
