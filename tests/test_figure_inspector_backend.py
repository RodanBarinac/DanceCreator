from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

import GUI_DanceCreator_App as app_module
from src.engine.models.Dance import getCripsData, getFigure
from src.engine.models.DanceFloor import DanceFloor


def _dance_file(path: Path) -> bytes:
    content = {
        "Name": "Inspector Preview",
        "Desc": "A one-figure preview fixture.",
        "shape": "1/4",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], ["1cLT", []]]]],
    }
    serialized = json.dumps(content, indent=2).encode("utf-8")
    path.write_bytes(serialized)
    return serialized


def test_dance_node_preview_is_read_only_and_uses_trace_incoming_floor(tmp_path, monkeypatch):
    dance_path = tmp_path / "Inspector Preview.json"
    original_contents = _dance_file(dance_path)
    original_mtime = dance_path.stat().st_mtime_ns
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance_response = client.get("/api/dances/Inspector%20Preview")
    assert dance_response.status_code == 200, dance_response.get_json()
    dance_before = dance_response.get_json()
    node_id = dance_before["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/Inspector%20Preview/nodes/{node_id}/preview",
        json={"anchor": [1, 0], "addons": ["B4", "E1c"]},
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    trace_record = next(
        record for record in dance_before["trace"] if record["nodeId"] == node_id
    )
    assert body["incomingFloor"] == trace_record["incomingFloor"]
    assert body["outgoingFloor"]
    assert body["crips"][0]["barRange"] == [1, 4]
    assert body["crips"][0]["text"].startswith("turns left hand")
    response_schema = json.loads(Path("schema/api_dance_node_preview_response.schema.json").read_text())
    response_shape = {
        **response_schema,
        "properties": {
            **response_schema["properties"],
            "crips": {"type": "array"},
            "incomingFloor": {"type": "object"},
            "outgoingFloor": {"type": "object"},
        },
    }
    validate(body, response_shape)
    line_schema = json.loads(Path("schema/api_crip_line.schema.json").read_text())
    for line in body["crips"]:
        validate(line, line_schema)
    floor_schema = json.loads(Path("schema/api_floor_snapshot.schema.json").read_text())
    validate(body["incomingFloor"], floor_schema)
    validate(body["outgoingFloor"], floor_schema)
    assert dance_path.read_bytes() == original_contents
    assert dance_path.stat().st_mtime_ns == original_mtime
    dance_after = client.get("/api/dances/Inspector%20Preview").get_json()
    assert dance_after["document"] == dance_before["document"]
    assert dance_after["trace"] == dance_before["trace"]


def test_catalog_preview_conflict_error_names_affected_dancers():
    response = app_module.app.test_client().post(
        "/api/figures/1cLT/preview",
        json={"anchor": [1, 0], "addons": ["B2", "B3"]},
    )

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "addon_conflict"
    assert "B2" in error["message"] and "B3" in error["message"]
    assert error["dancers"] == ["start position 1", "start position 2"]
    error_schema = json.loads(Path("schema/api_error.schema.json").read_text())
    validate(response.get_json(), error_schema)
    validate(
        {"status": "error", "error": "not_found", "message": "No figure", "code": 404},
        error_schema,
    )


def test_structured_crip_text_has_no_duplicate_dancer_and_uses_possessive_position():
    figure = getFigure("1cLT", [1, 0], ["B4", "E1c"])
    lines = getCripsData(figure, DanceFloor("catalog", 2))

    assert lines[0]["dancer"] == "1m"
    assert lines[0]["text"].startswith("turns left hand with 1w")
    assert "2w's position" in lines[0]["text"]
    assert not lines[0]["text"].startswith("1m ")


def test_dance_node_preview_errors_report_affected_dancers(tmp_path, monkeypatch):
    dance_path = tmp_path / "Inspector Preview Failure.json"
    _dance_file(dance_path)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Inspector%20Preview%20Failure").get_json()
    node_id = dance["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/Inspector%20Preview%20Failure/nodes/{node_id}/preview",
        json={"anchor": [99, 0], "addons": []},
    )

    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "figure_execution_failed"
    assert error["dancers"] == ["start position 1", "start position 2"]


def test_dance_node_preview_addon_conflicts_report_both_start_positions(tmp_path, monkeypatch):
    dance_path = tmp_path / "Inspector Preview Conflict.json"
    _dance_file(dance_path)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Inspector%20Preview%20Conflict").get_json()
    node_id = dance["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/Inspector%20Preview%20Conflict/nodes/{node_id}/preview",
        json={"anchor": [1, 0], "addons": ["B2", "B3"]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["dancers"] == [
        "start position 1", "start position 2"
    ]


def test_apply_rejection_for_addon_conflict_names_affected_dancers(tmp_path, monkeypatch):
    dance_path = tmp_path / "Inspector Proposal Conflict.json"
    original_contents = _dance_file(dance_path)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Inspector%20Proposal%20Conflict").get_json()
    node_id = dance["tree"]["children"][0]["id"]

    proposal_response = client.post(
        "/api/dances/Inspector%20Proposal%20Conflict/proposals",
        json={
            "baseRevision": dance["revision"],
            "command": {
                "type": "updateAddons",
                "nodeId": node_id,
                "addons": ["B2", "B3"],
            },
        },
    )
    assert proposal_response.status_code == 200, proposal_response.get_json()
    proposal_id = proposal_response.get_json()["proposal"]["proposalId"]

    response = client.post(
        "/api/dances/Inspector%20Proposal%20Conflict/apply",
        json={"proposalId": proposal_id, "baseRevision": dance["revision"]},
    )

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "validation_error"
    assert error["dancers"] == ["start position 1", "start position 2"]
    validate(response.get_json(), json.loads(Path("schema/api_error.schema.json").read_text()))
    assert dance_path.read_bytes() == original_contents


def test_apply_rejection_for_missing_dancers_names_affected_positions(tmp_path, monkeypatch):
    dance_path = tmp_path / "Inspector Proposal Position Failure.json"
    _dance_file(dance_path)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Inspector%20Proposal%20Position%20Failure").get_json()
    node_id = dance["tree"]["children"][0]["id"]
    proposal = client.post(
        "/api/dances/Inspector%20Proposal%20Position%20Failure/proposals",
        json={
            "baseRevision": dance["revision"],
            "command": {"type": "updateAnchor", "nodeId": node_id, "anchor": [99, 0]},
        },
    ).get_json()["proposal"]

    response = client.post(
        "/api/dances/Inspector%20Proposal%20Position%20Failure/apply",
        json={"proposalId": proposal["proposalId"], "baseRevision": dance["revision"]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["dancers"] == [
        "start position 1", "start position 2"
    ]


def test_update_occurrence_command_applies_anchor_and_addons_as_one_history_step(tmp_path, monkeypatch):
    dance_path = tmp_path / "Inspector Combined Edit.json"
    _dance_file(dance_path)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Inspector%20Combined%20Edit").get_json()
    node_id = dance["tree"]["children"][0]["id"]

    proposal = client.post(
        "/api/dances/Inspector%20Combined%20Edit/proposals",
        json={
            "baseRevision": dance["revision"],
            "command": {
                "type": "updateOccurrence",
                "nodeId": node_id,
                "anchor": [1, 0],
                "addons": ["B4"],
            },
        },
    )
    assert proposal.status_code == 200, proposal.get_json()
    applied = client.post(
        "/api/dances/Inspector%20Combined%20Edit/apply",
        json={
            "proposalId": proposal.get_json()["proposal"]["proposalId"],
            "baseRevision": dance["revision"],
        },
    )
    assert applied.status_code == 200, applied.get_json()
    assert applied.get_json()["revision"] == dance["revision"] + 1
    undone = client.post(
        "/api/dances/Inspector%20Combined%20Edit/undo",
        json={"baseRevision": applied.get_json()["revision"]},
    )
    assert undone.status_code == 200, undone.get_json()
    node = undone.get_json()["tree"]["children"][0]
    assert node.get("addons", []) == []
