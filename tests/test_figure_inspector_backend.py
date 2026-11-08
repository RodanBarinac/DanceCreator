from __future__ import annotations

import json
from pathlib import Path

from jsonschema import ValidationError, validate
import pytest

import GUI_DanceCreator_App as app_module
from src.engine.models.Dance import getCripsData, getFigure
from src.engine.models.DanceFloor import DanceFloor


def _dance_file(path: Path, shape="1/4") -> bytes:
    content = {
        "Name": "Inspector Preview",
        "Desc": "A one-figure preview fixture.",
        "shape": shape,
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
    assert trace_record["activeDancers"] == ["1m", "1w"]
    assert body["activeDancers"] == ["1m", "1w"]
    assert body["outgoingFloor"]
    assert body["crips"][0]["barRange"] == [1, 4]
    assert {line["nodeId"] for line in body["crips"]} == {node_id}
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


def test_node_preview_participants_follow_edited_anchor(tmp_path, monkeypatch):
    _dance_file(tmp_path / "Inspector Preview.json", shape="3/4")
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    model = client.get("/api/dances/Inspector%20Preview").get_json()
    node_id = model["tree"]["children"][0]["id"]
    response = client.post(
        f"/api/dances/Inspector%20Preview/nodes/{node_id}/preview",
        json={"anchor": [2, 0], "addons": []},
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["activeDancers"] == ["2m", "2w"]


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


def test_catalog_composite_preview_uses_declared_diagonal_starts_and_serial_execution():
    client = app_module.app.test_client()
    response = client.post(
        "/api/figures/1DR/preview",
        json={"anchor": [1, 0], "addons": []},
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["activeDancers"] == ["1m", "1w", "2m", "3w"]
    assert len(body["incomingFloor"]) == 4
    assert {tuple(item["position"]) for item in body["incomingFloor"].values()} == {
        (1, -1), (1.5, -0.5), (2.5, 0.5), (3, 1)
    }
    assert len(body["outgoingFloor"]) == 4
    assert [line["barRange"] for line in body["crips"]] == [
        [1, 4], [1, 4], [1, 4], [1, 4],
        [5, 8], [5, 8], [5, 8], [5, 8],
    ]
    assert {line["figureRef"] for line in body["crips"]} == {"H1DR"}
    invalid_anchor = client.post(
        "/api/figures/1DR/preview",
        json={"anchor": [1, "bad"], "addons": []},
    )
    assert invalid_anchor.status_code == 400
    assert invalid_anchor.get_json()["error"]["code"] == "invalid_preview"


def test_catalog_composite_preview_rejects_addons_instead_of_ignoring_them():
    response = app_module.app.test_client().post(
        "/api/figures/1DR/preview",
        json={"anchor": [1, 0], "addons": ["ELA"]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "composite_addons_unsupported"


def test_catalog_composite_rejects_addons_on_nested_composite(tmp_path, monkeypatch):
    inner = {
        "Name": "Inner Addon",
        "Desc": "Inner composite",
        "Formation": "turn",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], "1cWait"]]],
    }
    outer = {
        "Name": "Outer Addon",
        "Desc": "Outer composite",
        "Formation": "turn",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], ["Inner Addon", ["B4"]]]]],
    }
    for definition in (inner, outer):
        (tmp_path / f"{definition['Name']}.json").write_text(
            json.dumps(definition), encoding="utf-8"
        )
    (tmp_path / "1cWait.json").write_bytes(Path("data/Figures/1cWait.json").read_bytes())
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))

    response = app_module.app.test_client().post(
        "/api/figures/Outer%20Addon/preview",
        json={"anchor": [1, 0], "addons": []},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "composite_addons_unsupported"


def test_1dr_figurelist_schema_requires_group_children_to_be_nested():
    schema = json.loads(Path("schema/figure.schema.json").read_text())
    valid_definition = json.loads(Path("data/Figures/1DR.json").read_text())
    validate(valid_definition, schema)
    malformed = {
        **valid_definition,
        "FigureList": ["s", [[0, 0], "H1DR"], [[0, 0], "H1DR"]],
    }

    with pytest.raises(ValidationError):
        validate(malformed, schema)


def test_composite_node_preview_executes_nested_parallel_children_read_only(tmp_path, monkeypatch):
    composite = {
        "Name": "Nested Parallel",
        "Desc": "Two independent couple turns.",
        "Formation": "set",
        "Version": 3,
        "FigureList": [
            "s",
            [
                [
                    "p",
                    [
                        [[1, 0], ["1cLT", ["E1c"]]],
                        [[2, 0], "1cLT"],
                    ],
                ],
            ],
        ],
    }
    figure_path = tmp_path / "Nested Parallel.json"
    figure_path.write_text(json.dumps(composite), encoding="utf-8")
    (tmp_path / "1cLT.json").write_bytes(
        Path("data/Figures/1cLT.json").read_bytes()
    )
    dance_path = tmp_path / "Composite Preview.json"
    legacy_dance = {
        "Name": "Composite Preview",
        "shape": "2/4",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], "Nested Parallel"]]],
    }
    original_contents = json.dumps(legacy_dance).encode("utf-8")
    dance_path.write_bytes(original_contents)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Composite%20Preview").get_json()
    composite_node = dance["tree"]["children"][0]
    assert composite_node["type"] == "compositeOccurrence"

    response = client.post(
        f"/api/dances/Composite%20Preview/nodes/{composite_node['id']}/preview",
        json={"anchor": [0, 0], "addons": []},
    )

    assert response.status_code == 200, response.get_json()
    preview = response.get_json()
    trace_record = next(item for item in dance["trace"] if item["nodeId"] == composite_node["id"])
    assert preview["incomingFloor"] == trace_record["incomingFloor"]
    assert preview["activeDancers"] == ["1m", "1w", "2m", "2w"]
    assert [line["barRange"] for line in preview["crips"]] == [[1, 2]] * 4
    expected_ids = {
        record["nodeId"] for record in dance["trace"]
        if record["kind"] == "figure" and composite_node["id"] in record["path"]
    }
    assert {line["nodeId"] for line in preview["crips"]} == expected_ids
    assert {line["figureRef"] for line in preview["crips"]} == {"1cLT"}
    assert any("ends facing" in line["text"] for line in preview["crips"])
    assert len(preview["outgoingFloor"]) == 4
    addon_error = client.post(
        f"/api/dances/Composite%20Preview/nodes/{composite_node['id']}/preview",
        json={"anchor": [0, 0], "addons": ["E1c"]},
    )
    assert addon_error.status_code == 400
    assert addon_error.get_json()["error"]["code"] == "composite_addons_unsupported"
    assert dance_path.read_bytes() == original_contents
    after = client.get("/api/dances/Composite%20Preview").get_json()
    assert after["document"] == dance["document"]
    assert after["trace"] == dance["trace"]


def test_catalog_composite_parallel_conflict_is_reported_without_a_partial_floor(
    tmp_path, monkeypatch
):
    composite = {
        "Name": "Conflicting Composite",
        "Desc": "Two branches write the same positions.",
        "Formation": "turn",
        "Version": 3,
        "FigureList": [
            "s",
            [
                [
                    "p",
                    [
                        [[1, 0], ["1cLT", ["E1c"]]],
                        [[1, 0], ["1cLT", ["E1c"]]],
                    ],
                ],
            ],
        ],
    }
    (tmp_path / "Conflicting Composite.json").write_text(
        json.dumps(composite), encoding="utf-8"
    )
    (tmp_path / "1cLT.json").write_bytes(
        Path("data/Figures/1cLT.json").read_bytes()
    )
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))

    response = app_module.app.test_client().post(
        "/api/figures/Conflicting%20Composite/preview",
        json={"anchor": [0, 0], "addons": []},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "parallel_write_conflict"
    assert response.get_json()["error"]["dancers"] == ["1m", "1w"]
    assert "outgoingFloor" not in response.get_json()


def test_catalog_composite_missing_later_participant_returns_no_partial_result(
    tmp_path, monkeypatch
):
    composite = {
        "Name": "Unseeded Later Step",
        "Desc": "The later step requires a participant absent at the start.",
        "Formation": "turn",
        "Version": 3,
        "FigureList": [
            "s",
            [
                [[1, 0], "1cLT"],
                [[2, 0], "1cLT"],
            ],
        ],
    }
    (tmp_path / "Unseeded Later Step.json").write_text(
        json.dumps(composite), encoding="utf-8"
    )
    (tmp_path / "1cLT.json").write_bytes(
        Path("data/Figures/1cLT.json").read_bytes()
    )
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))

    response = app_module.app.test_client().post(
        "/api/figures/Unseeded%20Later%20Step/preview",
        json={"anchor": [0, 0], "addons": []},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "figure_execution_failed"
    assert "outgoingFloor" not in response.get_json()


def test_composite_node_preview_keeps_parent_bar_range():
    client = app_module.app.test_client()
    dance = client.get("/api/dances/Marries%20Wedding").get_json()
    node = next(
        item
        for item in dance["tree"]["children"]
        if item["figureRef"] == "Marries Wedding_Bar 9-12"
    )
    trace = next(item for item in dance["trace"] if item["nodeId"] == node["id"])
    assert trace["barRange"] == [9, 12]

    response = client.post(
        f"/api/dances/Marries%20Wedding/nodes/{node['id']}/preview",
        json={"anchor": node["anchor"], "addons": []},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["activeDancers"] == trace["activeDancers"]
    assert response.get_json()["crips"]
    assert {tuple(line["barRange"]) for line in response.get_json()["crips"]} == {(9, 12)}


def test_nested_composite_preview_includes_parent_anchor(tmp_path, monkeypatch):
    for name, child in (("Inner", "1cWait"), ("Outer", "Inner")):
        definition = {
            "Name": name,
            "Desc": name,
            "Formation": "test",
            "Version": 3,
            "FigureList": ["s", [[[0, 0], child]]],
        }
        (tmp_path / f"{name}.json").write_text(json.dumps(definition), encoding="utf-8")
    dance = {
        "Name": "Nested Anchor",
        "shape": "1/1",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], "Outer"]]],
    }
    (tmp_path / "Nested Anchor.json").write_text(json.dumps(dance), encoding="utf-8")
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    (tmp_path / "1cWait.json").write_bytes(Path("data/Figures/1cWait.json").read_bytes())
    client = app_module.app.test_client()
    model = client.get("/api/dances/Nested%20Anchor").get_json()
    inner = model["document"]["root"]["children"][0]["root"]["children"][0]
    trace = next(record for record in model["trace"] if record["nodeId"] == inner["id"])

    response = client.post(
        f"/api/dances/Nested%20Anchor/nodes/{inner['id']}/preview",
        json={"anchor": [0, 0], "addons": []},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["outgoingFloor"] == trace["outgoingFloor"]


def test_composite_node_preview_rejects_nested_composite_addons(tmp_path, monkeypatch):
    for name, child in (("Inner", "1cWait"), ("Outer", ["Inner", ["B4"]])):
        definition = {
            "Name": name,
            "Desc": name,
            "Formation": "test",
            "Version": 3,
            "FigureList": ["s", [[[0, 0], child]]],
        }
        (tmp_path / f"{name}.json").write_text(json.dumps(definition), encoding="utf-8")
    dance = {
        "Name": "Nested Addon",
        "shape": "1/1",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], "Outer"]]],
    }
    (tmp_path / "Nested Addon.json").write_text(json.dumps(dance), encoding="utf-8")
    (tmp_path / "1cWait.json").write_bytes(Path("data/Figures/1cWait.json").read_bytes())
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    model = client.get("/api/dances/Nested%20Addon").get_json()
    node_id = model["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/Nested%20Addon/nodes/{node_id}/preview",
        json={"anchor": [1, 0], "addons": []},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "composite_addons_unsupported"


def test_node_preview_crips_resolve_targets_beyond_incoming_set(tmp_path, monkeypatch):
    dance = {
        "Name": "Outlying Facing",
        "shape": "1/1",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], ["1cLT", ["E1c"]]]]],
    }
    (tmp_path / "Outlying Facing.json").write_text(json.dumps(dance), encoding="utf-8")
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    model = client.get("/api/dances/Outlying%20Facing").get_json()
    node_id = model["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/Outlying%20Facing/nodes/{node_id}/preview",
        json={"anchor": [1, 0], "addons": ["E1c"]},
    )

    assert response.status_code == 200, response.get_json()
    assert "2w's position" in response.get_json()["crips"][0]["text"]


def test_composite_node_preview_rejects_existing_composite_addons(tmp_path, monkeypatch):
    composite = {
        "Name": "Stored Addon Composite",
        "Desc": "A composite occurrence with a legacy wrapper add-on.",
        "Formation": "turn",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], "1cLT"]]],
    }
    (tmp_path / "Stored Addon Composite.json").write_text(
        json.dumps(composite), encoding="utf-8"
    )
    (tmp_path / "1cLT.json").write_bytes(
        Path("data/Figures/1cLT.json").read_bytes()
    )
    dance = {
        "Name": "Stored Addon Dance",
        "shape": "3/4",
        "Version": 3,
        "FigureList": [
            "s",
            [[[0, 0], ["Stored Addon Composite", ["B4"]]]],
        ],
    }
    (tmp_path / "Stored Addon Dance.json").write_text(
        json.dumps(dance), encoding="utf-8"
    )
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path))
    client = app_module.app.test_client()
    model = client.get("/api/dances/Stored%20Addon%20Dance").get_json()
    node = model["tree"]["children"][0]

    response = client.post(
        f"/api/dances/Stored%20Addon%20Dance/nodes/{node['id']}/preview",
        json={"anchor": [0, 0], "addons": []},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "composite_addons_unsupported"
    assert response.get_json()["error"]["details"]["addons"] == ["B4"]


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
