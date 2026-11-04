"""An empty accepted-route list must explain the observed search disposition."""

from typer.testing import CliRunner

from hop_design.cli import app
from hop_design.commands.construction import routes


def test_empty_accepted_listing_reports_rejection_and_coverage(monkeypatch):
    content = {
        "status": "infeasible",
        "accounting": {"examined_combinations": 1, "nominal_combinations": 1},
        "rows": [
            {
                "ordinal": 0,
                "status": "rejected",
                "rejection_reason": "source-preparation-incompatible",
                "truncation_reason": None,
            }
        ],
    }
    monkeypatch.setattr(routes, "load_receipt", lambda path: object())
    monkeypatch.setattr(routes, "navigation_content", lambda receipt: content)
    result = CliRunner().invoke(app, ["construction", "list", "a bundle"])
    assert result.exit_code == 0, result.output
    assert "No accepted route in this result" in result.output
    assert "1/1 examined" in result.output
    assert "0 accepted" in result.output
    assert "1 rejected" in result.output
    assert "source-preparation-incompatible" in result.output
    assert "construction list 'a bundle' --status all --group-by none" in result.output
    assert "does not identify a necessary or minimal repair" in result.output


def test_empty_truncated_result_does_not_claim_infeasibility(monkeypatch):
    content = {
        "status": "truncated",
        "accounting": {"examined_combinations": 0, "nominal_combinations": 4},
        "rows": [],
    }
    monkeypatch.setattr(routes, "load_receipt", lambda path: object())
    monkeypatch.setattr(routes, "navigation_content", lambda receipt: content)
    result = CliRunner().invoke(app, ["construction", "list", "a-bundle"])
    assert result.exit_code == 0
    assert "truncated" in result.output
    assert "0/4 examined" in result.output
    assert "infeasible" not in result.output
    assert "construction summary a-bundle" in result.output
