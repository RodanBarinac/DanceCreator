import json
from src.engine.models import Dance
from src.engine.models import DanceFloor as DF
from src.engine.figures.ComplexFigure import ComplexFigure
from src.engine.domain.dance_model import FigureOccurrence
from jsonschema import Draft7Validator, validate
from pathlib import Path


def test_structured_figure_crips_use_duration_addon_and_replacement_text():
    figure = Dance.getFigure("1cLT", [1, 0], ["B4", "E1c"])
    floor = DF.DanceFloor("catalog", 2)

    lines = Dance.getCripsData(figure, floor)

    legacy_lines = figure.getCrips(floor)
    assert len(lines) == 2
    assert [(line["dancer"], line["barRange"]) for line in lines] == [
        ("1m", [1, 4]),
        ("1w", [1, 4]),
    ]
    assert [line["text"] for line in lines] == [
        legacy_line.split(": ", 1)[1].removeprefix(f"{line['dancer']} ")
        for line, legacy_line in zip(lines, legacy_lines)
    ]
    assert all("ends facing" in line["text"] for line in lines)
    assert all(line["figureRef"] == "1cLT" for line in lines)



def test_structured_crips_accept_a_canonical_figure_node():
    floor = DF.DanceFloor("dance", 2)
    occurrence = FigureOccurrence(
        "turn-node", "1cLT", (1, 0), ("B4", "E1c")
    )

    lines = Dance.getCripsData(occurrence, floor)

    assert len(lines) == 2
    assert all(line["figureRef"] == "1cLT" for line in lines)
    assert all(line["barRange"] == [1, 4] for line in lines)
    assert all("ends facing" in line["text"] for line in lines)

def test_structured_crips_follow_serial_bar_ranges():
    floor = DF.DanceFloor("catalog", 1)
    four_bars = Dance.getFigure("1cWait", [1, 0], ["B4"])
    four_bars._CriptDesc = ["{Dancer} waits.", "{Dancer} waits."]
    two_bars = Dance.getFigure("1cWait", [1, 0])
    two_bars._CriptDesc = ["{Dancer} waits.", "{Dancer} waits."]
    dance = ComplexFigure("test")
    dance._FigureObjs = ["s", [four_bars, two_bars]]

    lines = Dance.getCripsData(dance, floor)

    assert [(line["figureRef"], line["barRange"]) for line in lines] == [
        ("1cWait", [1, 4]),
        ("1cWait", [1, 4]),
        ("1cWait", [5, 6]),
        ("1cWait", [5, 6]),
    ]


def test_structured_crips_follow_parallel_bar_ranges():
    floor = DF.DanceFloor("catalog", 2)
    first = Dance.getFigure("1cWait", [1, 0])
    second = Dance.getFigure("1cWait", [2, 0])
    first._CriptDesc = ["{Dancer} waits.", "{Dancer} waits."]
    second._CriptDesc = ["{Dancer} waits.", "{Dancer} waits."]
    dance = ComplexFigure("parallel")
    dance._FigureObjs = ["p", [first, second]]

    lines = Dance.getCripsData(dance, floor)

    assert [(line["dancer"], line["barRange"]) for line in lines] == [
        ("1m", [1, 2]),
        ("1w", [1, 2]),
        ("2m", [1, 2]),
        ("2w", [1, 2]),
    ]


def test_preview_response_includes_structured_crips_for_selected_addons():
    response = __import__("GUI_DanceCreator_App").app.test_client().post(
        "/api/figures/1cLT/preview",
        json={"anchor": [1, 0], "addons": ["B4", "E1c"]},
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["crips"][0] == {
        "figureRef": "1cLT",
        "dancer": "1m",
        "barRange": [1, 4],
        "text": "turns left hand with 1w and ends facing 2w's position.",
    }
    schema_path = Path("schema/api_figure_preview_response.schema.json").resolve()
    preview_schema = json.loads(schema_path.read_text())
    Draft7Validator.check_schema(preview_schema)
    assert set(preview_schema["required"]).issubset(body)
    assert preview_schema["properties"]["crips"]["$ref"] == "./api_crips.schema.json"


def test_dance_response_includes_structured_crips_from_trace_incoming_floors():
    response = __import__("GUI_DanceCreator_App").app.test_client().get(
        "/api/dances/Marries%20Wedding_all"
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["crips"]
    figure_records = [record for record in body["trace"] if record["kind"] == "figure"]
    for line in body["crips"]:
        assert set(line) == {"figureRef", "dancer", "barRange", "text"}
        assert isinstance(line["dancer"], str) and line["dancer"]
        assert len(line["barRange"]) == 2
        assert isinstance(line["text"], str) and line["text"]
        validate(
            line,
            json.loads(Path("schema/api_crip_line.schema.json").read_text()),
        )
        assert any(
            record["figureRef"] == line["figureRef"]
            and record["barRange"] == line["barRange"]
            and line["dancer"] in {
                entry["dancer"]["name"]
                for entry in record["incomingFloor"].values()
            }
            for record in figure_records
        )
