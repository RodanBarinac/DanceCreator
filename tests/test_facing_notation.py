"""Tests for symbolic EndFacing targets and runtime facing preservation."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

import GUI_DanceCreator_App as app_module
from src.engine.figures.SimpleFigure import SimpleFigure
from src.engine.figures.capabilities import FigureRepository
from src.engine.models.Dance import getFigure
from src.engine.models.DanceFloor import DanceFloor


def _figure_definition(end_facing, *, start=(0, -1), end=(0, -1), addon=None):
    return {
        "Name": "FacingNotation",
        "Desc": "A facing notation test figure",
        "Formation": "test",
        "Version": 2,
        "Bars": 1,
        "StartPos": [list(start)],
        "EndPos": [list(end)],
        "EndFacing": [end_facing],
        "CriptDesc": ["{Dancer} ends facing {Face}"],
        "Addons": addon or {},
    }


def _write_figure(tmp_path, definition, monkeypatch):
    figure_dir = tmp_path / "data" / "Figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    (figure_dir / "FacingNotation.json").write_text(
        json.dumps(definition), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    return figure_dir


@pytest.mark.parametrize(
    ("notation", "end", "gender", "expected"),
    [
        ("I", (0, -2), "male", (0, 0)),
        ("I", (0, 2), "female", (0, 0)),
        ("O", (0, -2), "male", (0, -4)),
        ("O", (0, 2), "female", (0, 4)),
        ("U", (3, 0.5), "female", (2, 0.5)),
        ("D", (3, 0.5), "male", (4, 0.5)),
        ("OwnL", (0, 2), "male", (0, -1)),
        ("OwnL", (0, -2), "female", (0, 1)),
        ("OpL", (0, -2), "male", (0, 1)),
        ("OpL", (0, 2), "female", (0, -1)),
    ],
)
def test_symbolic_facing_resolves_from_final_anchored_position(
    tmp_path, monkeypatch, notation, end, gender, expected
):
    _write_figure(
        tmp_path,
        _figure_definition(notation, end=end),
        monkeypatch,
    )
    figure = SimpleFigure("FacingNotation", [2, 0])
    floor = DanceFloor("facing")
    from src.engine.models.Dancer import Dancer

    dancer = next(
        dancer
        for dancer in (
            Dancer("1m", "male"),
            Dancer("1w", "female"),
        )
        if dancer.gender == gender
    )
    start = figure.posWithAnchor(figure.StartPos[0])
    floor.addDancer(dancer, start, [start[0] + 1, start[1]])

    outgoing = figure.DanceMove(floor)

    expected_target = [expected[0] + figure.Anchor[0], expected[1]]
    assert list(outgoing.DanceFloorMap[figure.posWithAnchor(figure.EndPos[0])][1]) == expected_target


def test_equals_preserves_incoming_direction_after_anchor_and_movement(
    tmp_path, monkeypatch
):
    _write_figure(
        tmp_path,
        _figure_definition("=", start=(0, -1), end=(2, 0.5)),
        monkeypatch,
    )
    figure = SimpleFigure("FacingNotation", [2, 3])
    floor = DanceFloor("facing")
    start = figure.posWithAnchor(figure.StartPos[0])
    from src.engine.models.Dancer import Dancer

    floor.addDancer(Dancer("1m", "male"), start, [start[0] + 1, start[1]])

    outgoing = figure.DanceMove(floor)

    final = figure.posWithAnchor(figure.EndPos[0])
    assert list(outgoing.DanceFloorMap[final][1]) == [final[0] + 1, final[1]]


@pytest.mark.parametrize(
    ("notation", "start", "end", "facing", "gender", "error"),
    [
        ("I", (0, -1), (0, 0), [1, 0], "male", "center"),
        ("O", (0, -1), (0, 0), [1, 0], "male", "center"),
        ("OwnL", (0, -1), (0, -1), [1, 0], "male", "already"),
        ("OpL", (0, -1), (0, 1), [1, 0], "male", "already"),
        ("=", (0, -1), (0, 1), None, "male", "incoming facing"),
        ("=", (0, -1), (0, 1), [1, -1], "male", "incoming facing"),
    ],
)
def test_symbolic_facing_rejects_ambiguous_or_invalid_targets(
    tmp_path, monkeypatch, notation, start, end, facing, gender, error
):
    _write_figure(
        tmp_path,
        _figure_definition(notation, start=start, end=end),
        monkeypatch,
    )
    figure = SimpleFigure("FacingNotation", [1, 0])
    from src.engine.models.Dancer import Dancer

    floor = DanceFloor("facing")
    absolute_start = figure.posWithAnchor(figure.StartPos[0])
    floor.addDancer(Dancer("1m", gender), absolute_start, facing)

    with pytest.raises(ValueError, match=error):
        figure.DanceMove(floor)


def test_m_facing_is_a_structured_unsupported_runtime_error(tmp_path, monkeypatch):
    _write_figure(tmp_path, _figure_definition("M"), monkeypatch)
    from src.engine.models.Dancer import Dancer

    floor = DanceFloor("facing")
    floor.addDancer(Dancer("1m", "male"), (0, -1), [0, 1])

    with pytest.raises(ValueError) as raised:
        getFigure("FacingNotation").DanceMove(floor)

    assert getattr(raised.value, "code", None) == "unsupported_facing_notation"
    assert "M" in str(raised.value)


def test_missing_endfacing_stores_a_concrete_same_row_default(tmp_path, monkeypatch):
    definition = _figure_definition([0, 1])
    del definition["EndFacing"]
    _write_figure(tmp_path, definition, monkeypatch)
    figure = getFigure("FacingNotation", [1, 0])

    outgoing = figure.DanceMove(DanceFloor("incoming", 1))

    assert list(outgoing.DanceFloorMap[(1, -1)][1]) == [1, 1]


def test_addon_facing_shorthand_is_a_real_write_and_conflicts(tmp_path, monkeypatch):
    definition = _figure_definition(
        [0, 1],
        addon={
            "Symbolic": {
                "Name": "Symbolic",
                "Desc": "Use shorthand",
                "Version": 1,
                "EndFacing": ["="],
            },
            "Coordinate": {
                "Name": "Coordinate",
                "Desc": "Use coordinates",
                "Version": 1,
                "EndFacing": [[2, 2]],
            },
        },
    )
    definition["EndFacing"] = [[0, 1]]
    figure_dir = _write_figure(tmp_path, definition, monkeypatch)

    figure = getFigure("FacingNotation", [1, 0], ["Symbolic"])
    assert figure.EndFacing == ["="]
    with pytest.raises(ValueError, match="Symbolic.*Coordinate|Coordinate.*Symbolic"):
        getFigure("FacingNotation", [1, 0], ["Symbolic", "Coordinate"])
    with pytest.raises(ValueError, match="Symbolic.*Coordinate|Coordinate.*Symbolic"):
        FigureRepository(figure_dir).validate_addons(
            "FacingNotation", ["Symbolic", "Coordinate"], path="root"
        )


@pytest.mark.parametrize("notation", ["unknown", "ownl", "OwnLine", "I/O"])
def test_loader_rejects_unknown_base_or_addon_facing_notation(
    tmp_path, monkeypatch, notation
):
    definition = _figure_definition(notation)
    _write_figure(tmp_path, definition, monkeypatch)

    with pytest.raises(ValueError, match="unsupported facing notation"):
        getFigure("FacingNotation")

    definition = _figure_definition(
        [0, 1],
        addon={
            "Bad": {
                "Name": "Bad",
                "Desc": "Unsupported facing",
                "Version": 1,
                "EndFacing": [notation],
            }
        },
    )
    _write_figure(tmp_path, definition, monkeypatch)
    with pytest.raises(ValueError, match="unsupported facing notation"):
        getFigure("FacingNotation")


@pytest.mark.parametrize("notation", ["=", "I", "O", "U", "D", "OwnL", "OpL", "M"])
def test_endfacing_schemas_accept_agreed_notation(notation):
    root = Path(__file__).resolve().parents[1]
    for schema_name in ("figure.schema.json", "api_figure_update_request.schema.json"):
        schema = json.loads((root / "schema" / schema_name).read_text(encoding="utf-8"))
        definition = _figure_definition(notation)
        definition["Addons"] = {
            "Patch": {
                "Name": "Patch",
                "Desc": "symbolic patch",
                "Version": 1,
                "EndFacing": [notation],
            }
        }
        assert list(Draft7Validator(schema).iter_errors(definition)) == []


@pytest.mark.parametrize("notation", ["unknown", "ownl", "OwnLine", "I/O"])
def test_endfacing_schemas_reject_unknown_notation(notation):
    root = Path(__file__).resolve().parents[1]
    for schema_name in ("figure.schema.json", "api_figure_update_request.schema.json"):
        schema = json.loads((root / "schema" / schema_name).read_text(encoding="utf-8"))
        definition = _figure_definition(notation)
        assert list(Draft7Validator(schema).iter_errors(definition))


def test_catalog_preview_uses_executed_facing_and_resolves_face_crip(
    tmp_path, monkeypatch
):
    figure_dir = _write_figure(
        tmp_path,
        _figure_definition("=", start=(0, -1), end=(1, 0),),
        monkeypatch,
    )
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_dir))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path / "data" / "Dances"))

    response = app_module.app.test_client().post(
        "/api/figures/FacingNotation/preview", json={"anchor": [2, 3]}
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    incoming = next(iter(payload["incomingFloor"].values()))
    outgoing = next(iter(payload["outgoingFloor"].values()))
    assert outgoing["facing"] == [incoming["facing"][0] + 1, outgoing["position"][1] - 4]
    assert payload["crips"][0]["text"].endswith("3m's position")


def test_dance_node_preview_uses_actual_incoming_facing_and_resolved_crip(
    tmp_path, monkeypatch
):
    figure_dir = _write_figure(
        tmp_path,
        _figure_definition("=", start=(0, -1), end=(1, 0)),
        monkeypatch,
    )
    dance_dir = tmp_path / "data" / "Dances"
    dance_dir.mkdir(parents=True, exist_ok=True)
    dance = {
        "Name": "FacingPreviewDance",
        "Desc": "A symbolic facing preview.",
        "shape": "1/1",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], ["FacingNotation", []]]]],
    }
    (dance_dir / "FacingPreviewDance.json").write_text(
        json.dumps(dance), encoding="utf-8"
    )
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_dir))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dance_dir))
    client = app_module.app.test_client()
    model = client.get("/api/dances/FacingPreviewDance").get_json()
    node_id = model["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/FacingPreviewDance/nodes/{node_id}/preview",
        json={"anchor": [1, 0], "addons": []},
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    ending = next(
        value
        for value in payload["outgoingFloor"].values()
        if value["position"] == [2, 0]
    )
    assert ending["facing"] == [2, 2]
    assert payload["crips"][0]["text"].endswith("position (2, 2)")


def test_dance_node_preview_returns_structured_unsupported_m_error(tmp_path, monkeypatch):
    figure_dir = _write_figure(
        tmp_path, _figure_definition("M", start=(0, -1), end=(0, -1)), monkeypatch
    )
    dance_dir = tmp_path / "data" / "Dances"
    dance_dir.mkdir(parents=True, exist_ok=True)
    dance = {
        "Name": "UnsupportedFacingDance",
        "Desc": "A dance with unsupported M notation.",
        "shape": "1/1",
        "Version": 3,
        "FigureList": ["s", [[[1, 0], ["FacingNotation", []]]]],
    }
    (dance_dir / "UnsupportedFacingDance.json").write_text(
        json.dumps(dance), encoding="utf-8"
    )
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_dir))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dance_dir))
    client = app_module.app.test_client()
    model = client.get("/api/dances/UnsupportedFacingDance").get_json()
    node_id = model["tree"]["children"][0]["id"]

    response = client.post(
        f"/api/dances/UnsupportedFacingDance/nodes/{node_id}/preview",
        json={"anchor": [1, 0], "addons": []},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "unsupported_facing_notation", response.get_json()


def test_preview_does_not_blame_m_for_an_unexecuted_later_figure(tmp_path, monkeypatch):
    figure_dir = _write_figure(tmp_path, _figure_definition("M"), monkeypatch)
    dance_dir = tmp_path / "data" / "Dances"
    dance_dir.mkdir(parents=True, exist_ok=True)
    dance = {
        "Name": "BlockedFacingDance",
        "Desc": "A later figure has no trace.",
        "shape": "1/1",
        "Version": 3,
        "FigureList": ["s", [
            [[1, 0], ["FacingNotation", []]],
            [[1, 0], ["FacingNotation", []]],
        ]],
    }
    (dance_dir / "BlockedFacingDance.json").write_text(json.dumps(dance), encoding="utf-8")
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_dir))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dance_dir))
    client = app_module.app.test_client()
    model = client.get("/api/dances/BlockedFacingDance").get_json()
    later_id = model["tree"]["children"][1]["id"]

    response = client.post(
        f"/api/dances/BlockedFacingDance/nodes/{later_id}/preview",
        json={"anchor": [1, 0], "addons": []},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "preview_failed"


def test_catalog_preview_returns_structured_unsupported_m_error(tmp_path, monkeypatch):
    figure_dir = _write_figure(tmp_path, _figure_definition("M"), monkeypatch)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_dir))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path / "data" / "Dances"))

    response = app_module.app.test_client().post(
        "/api/figures/FacingNotation/preview", json={"anchor": [1, 0]}
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "unsupported_facing_notation"


@pytest.mark.parametrize(
    ("notation", "expected"),
    [
        ("I", "1m ends facing between 1c's position"),
        ("O", "1m ends facing position (1, -2)"),
    ],
)
def test_face_placeholder_resolves_symbolic_targets(
    tmp_path, monkeypatch, notation, expected
):
    _write_figure(
        tmp_path,
        _figure_definition(notation),
        monkeypatch,
    )
    figure = getFigure("FacingNotation", [1, 0])

    assert figure.getCrips(DanceFloor("incoming", 1)) == [
        f"1 - 1: {expected}"
    ]


def test_one_couple_wait_preserves_incoming_facing():
    wait = getFigure("1cWait", [1, 0])
    assert wait.EndFacing == ["=", "="]

    floor = DanceFloor("wait", 1)
    floor.DanceFloorMap[(1, -1)][1] = [2, 0]
    floor.DanceFloorMap[(1, 1)][1] = [3, 2]

    outgoing = wait.DanceMove(floor)

    assert list(outgoing.DanceFloorMap[(1, -1)][1]) == [2, 0]
    assert list(outgoing.DanceFloorMap[(1, 1)][1]) == [3, 2]
