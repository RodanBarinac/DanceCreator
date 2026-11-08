import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

import GUI_DanceCreator_App as app_module
from src.engine.domain.dance_model import DanceDocument, FigureOccurrence, GroupNode
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.execution.executor import execute_document
from src.engine.figures.capabilities import FigureRepository
from src.engine.models.Dance import getFigure
from src.engine.models.DanceFloor import DanceFloor


def _definition(**addons):
    return {
        "Name": "NullFacing",
        "Desc": "A test figure",
        "Formation": "turn",
        "Version": 2,
        "Bars": 1,
        "StartPos": [[0, -1]],
        "EndPos": [[0, 0]],
        "EndFacing": [[0, 1]],
        "CriptDesc": ["Dancer ends in position"],
        "Addons": addons,
    }


def _write_figure(directory, definition):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{definition['Name']}.json"
    path.write_text(json.dumps(definition), encoding="utf-8")
    return path


def _repo_and_working_directory(tmp_path, monkeypatch, definition):
    figure_directory = tmp_path / "data" / "Figures"
    _write_figure(figure_directory, definition)
    monkeypatch.chdir(tmp_path)
    return FigureRepository(figure_directory)


def test_null_reset_uses_final_anchored_position_in_execution(tmp_path, monkeypatch):
    definition = _definition(
        Reset={
            "Name": "Reset",
            "Desc": "Reset facing",
            "Version": 1,
            "EndPos": [[2, 0.5]],
            "EndFacing": [None],
        }
    )
    repository = _repo_and_working_directory(tmp_path, monkeypatch, definition)
    incoming = FloorState({
        (1, 1): FloorEntry("1m", "male", (1, -1)),
    })
    document = DanceDocument(
        1,
        {},
        GroupNode(
            "root",
            "series",
            (FigureOccurrence("figure", "NullFacing", (1, 2), ("Reset",)),),
        ),
    )

    result = execute_document(document, incoming, repository)

    assert result.status == "completed"
    ending = result.outgoing_floor.positions[(3, 2.5)]
    assert ending.dancer_name == "1m"
    assert ending.facing == (3, -2.5)


def test_empty_array_keeps_base_end_facing_override(tmp_path, monkeypatch):
    definition = _definition(
        Keep={
            "Name": "Keep",
            "Desc": "Keep facing",
            "Version": 1,
            "EndPos": [[2, 0.5]],
            "EndFacing": [[]],
        }
    )
    _repo_and_working_directory(tmp_path, monkeypatch, definition)

    figure = getFigure("NullFacing", [1, 2], ["Keep"])
    ending_floor = figure.DanceMove(DanceFloor("test", 2))
    ending = ending_floor.DanceFloorMap[(3, 2.5)]

    assert ending[1] == (1, 3)


@pytest.mark.parametrize(
    "writes",
    [
        ([None], [None]),
        ([None], [[4, 5]]),
        ([[4, 5]], [None]),
    ],
)
def test_null_and_coordinate_endfacing_writes_conflict_in_loader_and_capabilities(
    tmp_path, monkeypatch, writes
):
    definition = _definition(
        First={"Name": "First", "Desc": "first", "Version": 1, "EndFacing": writes[0]},
        Second={"Name": "Second", "Desc": "second", "Version": 1, "EndFacing": writes[1]},
    )
    repository = _repo_and_working_directory(tmp_path, monkeypatch, definition)

    with pytest.raises(ValueError, match="First.*Second|Second.*First"):
        getFigure("NullFacing", [0, 0], ["First", "Second"])
    with pytest.raises(ValueError, match="First.*Second|Second.*First"):
        repository.validate_addons("NullFacing", ["First", "Second"], path="root")


def test_null_reset_can_combine_with_disjoint_addon_writes(tmp_path, monkeypatch):
    definition = _definition(
        Reset={
            "Name": "Reset",
            "Desc": "reset",
            "Version": 1,
            "EndFacing": [None, []],
        },
        FaceOther={
            "Name": "FaceOther",
            "Desc": "face other dancer",
            "Version": 1,
            "EndFacing": [[], [4, 5]],
        },
        Move={
            "Name": "Move",
            "Desc": "move",
            "Version": 1,
            "EndPos": [[2, 0.5], []],
        },
    )
    definition["StartPos"] = [[0, -1], [0, 1]]
    definition["EndPos"] = [[0, -1], [0, 1]]
    definition["EndFacing"] = [[0, 1], [0, -1]]
    definition["CriptDesc"] = ["", ""]
    repository = _repo_and_working_directory(tmp_path, monkeypatch, definition)

    repository.validate_addons(
        "NullFacing", ["Reset", "FaceOther", "Move"], path="root"
    )
    figure = getFigure("NullFacing", [1, 2], ["Reset", "FaceOther", "Move"])

    assert figure.EndFacing == [None, [4, 5]]
    assert figure.EndPos == [[2, 0.5], (0, 1)]


@pytest.mark.parametrize(
    ("field", "values"),
    [
        ("StartPos", [None]),
        ("EndPos", [None]),
        ("Partner", [None]),
        ("CriptDesc", [None]),
        ("CriptReplace", [None]),
        ("EndPos", [[None, 0]]),
        ("EndFacing", [[None, 0]]),
    ],
)
def test_null_is_rejected_outside_endfacing_reset_entries(
    tmp_path, monkeypatch, field, values
):
    addon = {"Name": "Bad", "Desc": "bad", "Version": 1, field: values}
    definition = _definition(Bad=addon)
    repository = _repo_and_working_directory(tmp_path, monkeypatch, definition)

    with pytest.raises(ValueError, match="null|None|entry|array"):
        getFigure("NullFacing", [0, 0], ["Bad"])
    with pytest.raises(ValueError, match="null|None|entry|array"):
        repository.get_capabilities("NullFacing")


@pytest.mark.parametrize(
    "schema_name",
    ["figure.schema.json", "api_figure_update_request.schema.json"],
)
def test_addon_endfacing_schema_allows_null_but_other_addon_arrays_reject_it(schema_name):
    schema = json.loads(Path("schema", schema_name).read_text(encoding="utf-8"))
    valid = _definition(
        Reset={
            "Name": "Reset",
            "Desc": "reset",
            "Version": 1,
            "EndFacing": [None, []],
        }
    )
    errors = list(Draft7Validator(schema).iter_errors(valid))
    assert errors == []

    for field in ("StartPos", "EndPos", "Partner", "CriptDesc", "CriptReplace"):
        invalid = json.loads(json.dumps(valid))
        invalid["Addons"]["Reset"][field] = [None]
        assert list(Draft7Validator(schema).iter_errors(invalid)), field
    invalid = json.loads(json.dumps(valid))
    invalid["Addons"]["Reset"]["EndFacing"] = [[None, 0]]
    assert list(Draft7Validator(schema).iter_errors(invalid))


def test_catalog_preview_reports_null_reset_facing_after_anchor(tmp_path, monkeypatch):
    definition = _definition(
        Reset={
            "Name": "Reset",
            "Desc": "Reset facing",
            "Version": 1,
            "EndPos": [[2, 0.5]],
            "EndFacing": [None],
        }
    )
    figure_directory = tmp_path / "data" / "Figures"
    _write_figure(figure_directory, definition)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_directory))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path / "data" / "Dances"))

    response = app_module.app.test_client().post(
        "/api/figures/NullFacing/preview",
        json={"anchor": [1, 2], "addons": ["Reset"]},
    )

    assert response.status_code == 200, response.get_json()
    ending = next(
        value
        for value in response.get_json()["outgoingFloor"].values()
        if value["position"] == [3, 2.5]
    )
    assert ending["facing"] == [3, -2.5]


def test_face_placeholder_uses_null_reset_target_in_catalog_preview(tmp_path, monkeypatch):
    definition = _definition(
        Reset={
            "Name": "Reset",
            "Desc": "Reset facing",
            "Version": 1,
            "EndFacing": [None],
        }
    )
    definition["EndPos"] = [[0, -1]]
    definition["EndFacing"] = [[1, -1]]
    definition["CriptDesc"] = ["Dancer ends facing {Face}"]
    figure_directory = tmp_path / "data" / "Figures"
    _write_figure(figure_directory, definition)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figure_directory))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(tmp_path / "data" / "Dances"))

    response = app_module.app.test_client().post(
        "/api/figures/NullFacing/preview",
        json={"anchor": [2, 0], "addons": ["Reset"]},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["crips"][0]["text"] == "Dancer ends facing 2w's position"


def test_face_placeholder_resets_after_applying_nonzero_column_anchor(tmp_path, monkeypatch):
    definition = _definition(
        Reset={"Name": "Reset", "Desc": "reset", "Version": 1, "EndFacing": [None]}
    )
    definition["EndPos"] = [[0, -1]]
    definition["CriptDesc"] = ["Dancer ends facing {Face}"]
    _repo_and_working_directory(tmp_path, monkeypatch, definition)
    figure = getFigure("NullFacing", [1, 2], ["Reset"])
    floor = DanceFloor("test", 2)

    assert figure.DanceMove(floor).DanceFloorMap[(1, 1)][1] == [1, -1]
    assert figure.getCrips(floor) == ["1 - 1: Dancer ends facing 1m's position"]
