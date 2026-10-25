import json
from pathlib import Path

import jsonschema
import pytest

import GUI_DanceCreator_App as app_module
from src.engine.domain.dance_model import DanceDocument, FigureOccurrence, GroupNode
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.execution.executor import FigureExecutionError, execute_document
from src.engine.figures.SimpleFigure import SimpleFigure
from src.engine.figures.capabilities import FigureRepository
from src.engine.models import DanceFloor
from src.engine.validators.DancefloorContractValidator import DancefloorSerializer


def _definition(**overrides):
    value = {
        "Version": 2,
        "Name": "Preview Step",
        "Desc": "test figure",
        "Bars": 1,
        "Formation": "1x1",
        "StartPos": [[0, -1], [0, 1]],
        "EndPos": [[0, -1], [0, 1]],
        "EndFacing": [[], []],
        "CriptDesc": ["wait", "wait"],
        "Addons": {},
    }
    value.update(overrides)
    return value


@pytest.fixture
def figure_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "Figures"
    root.mkdir(parents=True)
    return root


def test_start_dancers_and_start_facing_load_as_parallel_figure_metadata(figure_root):
    (figure_root / "Metadata.json").write_text(
        json.dumps(_definition(
            StartDancers=["2m", "1w"],
            StartFacing=[[1, -1], []],
        )),
        encoding="utf-8",
    )

    figure = SimpleFigure("Metadata")

    assert figure.StartDancers == ["2m", "1w"]
    assert figure.StartFacing == [(1, -1), ""]


@pytest.mark.parametrize(
    "start_dancers, message",
    [
        (["1m"], "StartDancers.*StartPos"),
        (["one", "1w"], "invalid.*dancer|StartDancers"),
        (["1m", "1m"], "duplicate.*1m|StartDancers"),
        (["2m", "", ""], "duplicate.*2m|StartDancers"),
    ],
)
def test_start_dancers_reject_invalid_length_names_and_post_fallback_collisions(
    figure_root, start_dancers, message
):
    (figure_root / "Invalid.json").write_text(
        json.dumps(_definition(
            StartPos=[[0, -1], [0, 1], [1, -1]],
            EndPos=[[0, -1], [0, 1], [1, -1]],
            EndFacing=[[], [], []],
            CriptDesc=["wait", "wait", "wait"],
            StartDancers=start_dancers,
        )),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=message):
        SimpleFigure("Invalid")


def test_start_facing_must_be_parallel_to_start_positions(figure_root):
    (figure_root / "InvalidFacing.json").write_text(
        json.dumps(_definition(StartFacing=[[1, -1]])),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="StartFacing.*StartPos"):
        SimpleFigure("InvalidFacing")



def test_start_declaration_lengths_are_checked_after_start_position_addons(figure_root):
    (figure_root / "Extended.json").write_text(
        json.dumps(_definition(Addons={
            "Extend": {
                "Name": "Extend",
                "Desc": "Add a third active start",
                "Version": 1,
                "StartPos": [[], [], [1, -1]],
            }
        })),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="StartDancers.*effective StartPos"):
        SimpleFigure("Extended", Addons=["Extend"])


def test_figure_schemas_declare_start_dancer_and_facing_fields():
    root = Path(__file__).resolve().parents[1] / "schema"
    for name in ("figure.schema.json", "api_figure_update_request.schema.json"):
        schema = json.loads((root / name).read_text(encoding="utf-8"))
        assert schema["properties"]["StartDancers"]["type"] == "array"
        assert schema["properties"]["StartFacing"]["type"] == "array"
        jsonschema.Draft7Validator.check_schema(schema)
        field_schema = {
            "type": "object",
            "properties": {
                "StartDancers": schema["properties"]["StartDancers"],
                "StartFacing": schema["properties"]["StartFacing"],
            },
        }
        validator = jsonschema.Draft7Validator(field_schema)
        assert validator.is_valid({"StartDancers": ["2m", ""], "StartFacing": [[0.5, -0.5], []]})
        assert not validator.is_valid({"StartDancers": ["2x"], "StartFacing": [[0, -1]]})
        assert not validator.is_valid({"StartFacing": [[0]]})


def test_default_facing_reflects_across_center_line_in_floor_and_serializer():
    floor = DanceFloor.DanceFloor("centered", 2)
    assert floor.DanceFloorMap[(2, -1)][1] == [2, 1]
    assert floor.DanceFloorMap[(2, 1)][1] == [2, -1]
    for entry in floor.DanceFloorMap.values():
        entry[1] = None

    serialized = DancefloorSerializer.serialize_dancefloor(
        "centered", 2, 0, floor.DanceFloorMap
    )

    assert serialized["positions"]["2m"]["facing"] == [2, 1]
    assert serialized["positions"]["2w"]["facing"] == [2, -1]


@pytest.fixture
def preview_client(tmp_path, monkeypatch):
    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()
    (figures / "Preview.json").write_text(json.dumps(_definition()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


def test_canonical_preview_default_facing_is_same_row_opposite_line(preview_client):
    response = preview_client.post("/api/figures/Preview/preview", json={"anchor": [2, 0]})
    assert response.status_code == 200, response.get_json()
    incoming = response.get_json()["incomingFloor"]
    by_name = {entry["dancer"]["name"]: entry for entry in incoming.values()}
    assert by_name["1m"]["facing"] == [2, 1]
    assert by_name["1w"]["facing"] == [2, -1]



def test_preview_empty_declarations_use_automatic_dancers_and_default_facing(preview_client):
    import GUI_DanceCreator_App as app

    figure_path = Path(app.FIGURES_DIR) / "Preview.json"
    definition = json.loads(figure_path.read_text(encoding="utf-8"))
    definition["StartDancers"] = ["", ""]
    definition["StartFacing"] = [[], []]
    figure_path.write_text(json.dumps(definition), encoding="utf-8")

    response = preview_client.post("/api/figures/Preview/preview", json={"anchor": [2, 0]})
    assert response.status_code == 200, response.get_json()
    incoming = response.get_json()["incomingFloor"]
    by_name = {entry["dancer"]["name"]: entry for entry in incoming.values()}
    assert set(by_name) == {"1m", "1w"}
    assert by_name["1m"]["facing"] == [2, 1]
    assert by_name["1w"]["facing"] == [2, -1]


def test_h1dr_pilot_preview_uses_declared_names_gender_and_start_facing(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "data" / "Figures" / "H1DR.json"
    definition = json.loads(source.read_text(encoding="utf-8"))
    assert definition["StartDancers"] == ["2m", "1w", "1m", "3w"]
    assert definition["StartFacing"] == [[0.5, -0.5], [0, -1], [2, 1], [1.5, 0.5]]

    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()
    (figures / "H1DR.json").write_text(json.dumps(definition), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        response = client.post("/api/figures/H1DR/preview", json={"anchor": [1, 0]})

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    incoming = {item["dancer"]["name"]: item for item in body["incomingFloor"].values()}
    assert set(incoming) == {"2m", "1w", "1m", "3w"}
    assert incoming["2m"]["dancer"]["gender"] == "male"
    assert incoming["1w"]["dancer"]["gender"] == "female"
    assert incoming["1m"]["dancer"]["gender"] == "male"
    assert incoming["3w"]["dancer"]["gender"] == "female"
    assert incoming["2m"]["facing"] == [1.5, -0.5]
    assert incoming["1w"]["facing"] == [1, -1]
    assert incoming["1m"]["facing"] == [3, 1]
    assert incoming["3w"]["facing"] == [2.5, 0.5]
    # The renderer derives couple color from the leading couple number in dancer.name.
    assert {name: int(name[:-1]) for name in incoming} == {
        "2m": 2, "1w": 1, "1m": 1, "3w": 3
    }



def test_six_catalog_figures_validate_and_preview_with_declared_identity_and_facing(
    tmp_path, monkeypatch
):
    catalog = Path(__file__).resolve().parents[1] / "data" / "Figures"
    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()

    expected_dancers = {
        "H1DR": ["2m", "1w", "1m", "3w"],
        "H2DR": ["3m", "1w", "1m", "2w"],
        "HLReelAU": ["2m", "1w", "2w"],
        "HLReelAD": ["2m", "1w", "2w"],
        "HRReelAU": ["2m", "1w", "2w"],
        "HRReelAD": ["2m", "1w", "2w"],
    }
    for name in expected_dancers:
        source = catalog / f"{name}.json"
        (figures / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    app_module.app.config["TESTING"] = True

    for name, dancers in expected_dancers.items():
        figure = SimpleFigure(name)
        assert figure.StartDancers == dancers
        assert len(figure.StartDancers) == len(figure.StartPos)
        assert len(set(figure.StartDancers)) == len(figure.StartDancers)

    for name, expected_facing in {
        "HLReelAU": [[0, 1], [0, -1], [0, -1]],
        "HRReelAU": [[0, 1], [0, 1], [0, -1]],
        "HRReelAD": [[0, 1], [0, -1], [0, -1]],
        "HLReelAD": [[0, 1], [0, 1], [0, -1]],
    }.items():
        definition = json.loads((figures / f"{name}.json").read_text(encoding="utf-8"))
        assert definition["Name"] == name
        assert definition["StartFacing"] == expected_facing

    with app_module.app.test_client() as client:
        for name, dancers in expected_dancers.items():
            response = client.post(f"/api/figures/{name}/preview", json={"anchor": [1, 0]})
            assert response.status_code == 200, (name, response.get_json())
            incoming = {
                item["dancer"]["name"]: item
                for item in response.get_json()["incomingFloor"].values()
            }
            assert set(incoming) == set(dancers)
            for dancer in dancers:
                expected_gender = "male" if dancer.endswith("m") else "female"
                assert incoming[dancer]["dancer"]["gender"] == expected_gender

        h2dr = client.post("/api/figures/H2DR/preview", json={"anchor": [1, 0]})
        incoming = {
            item["dancer"]["name"]: item
            for item in h2dr.get_json()["incomingFloor"].values()
        }
        assert incoming["3m"]["facing"] == [2.5, -0.5]
        assert incoming["1w"]["facing"] == [3, -1]
        assert incoming["1m"]["facing"] == [1, 1]
        assert incoming["2w"]["facing"] == [1.5, 0.5]

@pytest.mark.parametrize(
    "name, expected_facing",
    [
        ("HLReelAU", [[0, 1], [0, -1], [0, -1]]),
        ("HRReelAU", [[0, 1], [0, 1], [0, -1]]),
        ("HRReelAD", [[0, 1], [0, -1], [0, -1]]),
        ("HLReelAD", [[0, 1], [0, 1], [0, -1]]),
    ],
)
def test_half_reel_declared_facing_validates_and_appears_in_isolated_preview(
    name, expected_facing, tmp_path, monkeypatch
):
    catalog = Path(__file__).resolve().parents[1] / "data" / "Figures"
    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()
    source = catalog / f"{name}.json"
    (figures / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    app_module.app.config["TESTING"] = True

    figure = SimpleFigure(name)
    assert figure.StartFacing == [tuple(target) for target in expected_facing]

    with app_module.app.test_client() as client:
        response = client.post(f"/api/figures/{name}/preview", json={"anchor": [1, 0]})

    assert response.status_code == 200, response.get_json()
    incoming = {
        item["dancer"]["name"]: item
        for item in response.get_json()["incomingFloor"].values()
    }
    assert set(incoming) == {"2m", "1w", "2w"}
    for dancer, target in zip(("2m", "1w", "2w"), expected_facing):
        assert incoming[dancer]["facing"] == [1 + target[0], target[1]]


def test_start_facing_is_ignored_during_dance_execution_and_missing_start_is_rejected(figure_root):
    (figure_root / "Step.json").write_text(
        json.dumps(_definition(StartDancers=["2w", "1m"], StartFacing=[[99, 99], [99, 99]], EndFacing=[[], []])),
        encoding="utf-8",
    )
    repository = FigureRepository(figure_root)
    root = GroupNode("root", "series", (FigureOccurrence("step", "Step", (1, 0), ()),))
    document = DanceDocument(1, {}, root)
    initial = FloorState({
        (1, -1): FloorEntry("1m", "male", (7, 7)),
        (1, 1): FloorEntry("1w", "female", (8, 8)),
    })

    result = execute_document(document, initial, repository)
    assert result.trace_records[-1].incoming_floor.positions[(1, -1)].facing == (7, 7)
    assert result.outgoing_floor.positions[(1, -1)].dancer_name == "1m"
    assert result.outgoing_floor.positions[(1, 1)].dancer_name == "1w"
    assert result.outgoing_floor.positions[(1, -1)].facing in (None, ())

    missing = FloorState({(1, -1): FloorEntry("1m", "male", (1, 1))})
    with pytest.raises(FigureExecutionError, match="Missing dancer.*StartPos"):
        execute_document(document, missing, repository)
