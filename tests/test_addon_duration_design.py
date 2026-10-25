"""TDD coverage for reusable duration addons and addon conflict handling."""

import json
from pathlib import Path

import pytest

from src.engine.domain.dance_model import DanceDocument, FigureOccurrence, GroupNode
from src.engine.execution.duration import analyze_durations
from src.engine.execution.combine import FloorState
from src.engine.execution.executor import execute_document
from src.engine.figures.capabilities import FigureRepository
from src.engine.models.Dance import getFigure
from src.engine.figures.SimpleFigure import SimpleFigure
from src.engine.models.DanceFloor import DanceFloor


@pytest.mark.parametrize(("addon", "expected"), [("B3", 3), ("B8", 8)])
def test_arbitrary_duration_addons_override_figure_duration(addon, expected):
    figure = getFigure("1cLT", [1, 0], [addon])
    assert figure.Bars == expected
    moved = figure.DanceMove(DanceFloor("duration", 2))
    assert moved.AktBar == 1 + expected


def test_duration_addon_can_shorten_figure_and_is_not_defined_in_figure_file():
    figure = getFigure("1cLT", [1, 0], ["B3"])
    definition = json.loads(Path("data/Figures/1cLT.json").read_text(encoding="utf-8"))
    assert figure.Bars == 3
    assert "B3" not in definition.get("Addons", {})
    assert "B4" not in definition.get("Addons", {})


@pytest.mark.parametrize("invalid", ["B0", "B03", "b3", "B3x", "B"])
def test_malformed_duration_addon_names_are_not_accepted(invalid):
    with pytest.raises((ValueError, KeyError), match="addon|duration|B[0-9]|supported"):
        getFigure("H1DR", [0, 0], [invalid])


def test_figure_file_cannot_define_parameterized_duration_addon(tmp_path):
    path = tmp_path / "Invalid.json"
    path.write_text(json.dumps({"Name": "Invalid", "Version": 2, "Bars": 2,
        "Addons": {"B4": {"Name": "B4", "Bars": 4}}}), encoding="utf-8")
    with pytest.raises(ValueError, match="B<n>|duration addon|B4"):
        FigureRepository(tmp_path).get_definition("Invalid")


def test_two_duration_addons_conflict_with_both_names_reported():
    with pytest.raises(ValueError, match="B3.*B8|B8.*B3"):
        getFigure("H1DR", [0, 0], ["B3", "B8"])


def test_same_addon_field_and_dancer_conflicts_but_different_writes_combine(tmp_path, monkeypatch):
    definition = {
        "Name": "AddonConflict", "Version": 2, "Bars": 2,
        "StartPos": [[0, -1], [0, 1]], "EndPos": [[0, -1], [0, 1]],
        "EndFacing": [[], []], "Partner": [[0, 1], [0, -1]],
        "CriptDesc": ["Dancer waits in own place", "Dancer waits in own place"],
        "Addons": {
            "A": {"Name": "A", "Version": 1, "EndPos": [[1, 1]]},
            "B": {"Name": "B", "Version": 1, "EndPos": [[2, 2]]},
            "C": {"Name": "C", "Version": 1, "EndPos": [[], [3, 3]]},
            "D": {"Name": "D", "Version": 1, "EndFacing": [[4, 4]]},
            "E": {"Name": "E", "Version": 1, "EndPos": [[1, 1]]},
        },
    }
    (tmp_path / "data" / "Figures").mkdir(parents=True)
    (tmp_path / "data" / "Figures" / "AddonConflict.json").write_text(json.dumps(definition), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="A.*B.*EndPos.*dancer 1|B.*A.*EndPos.*dancer 1"):
        getFigure("AddonConflict", [0, 0], ["A", "B"])
    with pytest.raises(ValueError, match="A.*E.*EndPos.*dancer 1|E.*A.*EndPos.*dancer 1"):
        getFigure("AddonConflict", [0, 0], ["A", "E"])
    combined = getFigure("AddonConflict", [0, 0], ["A", "C", "D"])
    assert combined.EndPos == [[1, 1], [3, 3]]
    assert combined.EndFacing == [[4, 4], ""]



@pytest.mark.parametrize(
    ("field", "left", "right"),
    [
        ("StartPos", [[1, 1]], [[2, 2]]),
        ("Partner", [[1, 1]], [[2, 2]]),
        ("CriptDesc", ["ends left"], ["ends right"]),
    ],
)
def test_conflicts_cover_start_positions_partner_and_instruction_replacements(
    tmp_path, monkeypatch, field, left, right
):
    if field == "CriptDesc":
        addon_left = {"CriptDesc": left, "CriptReplace": ["wait"]}
        addon_right = {"CriptDesc": right, "CriptReplace": ["wait"]}
        definition = {
            "Name": "TextConflict", "Version": 2, "Bars": 2,
            "StartPos": [[0, -1]], "EndPos": [[0, -1]],
            "CriptDesc": ["Dancer waits"],
            "Addons": {
                "Left": {"Name": "Left", "Version": 1, **addon_left},
                "Right": {"Name": "Right", "Version": 1, **addon_right},
            },
        }
    else:
        definition = {
            "Name": "FieldConflict", "Version": 2, "Bars": 2,
            "StartPos": [[0, -1]], "EndPos": [[0, -1]],
            "Partner": [[0, 1]], "CriptDesc": ["Dancer waits"],
            "Addons": {
                "Left": {"Name": "Left", "Version": 1, field: left},
                "Right": {"Name": "Right", "Version": 1, field: right},
            },
        }
    figure_name = definition["Name"]
    (tmp_path / "data" / "Figures").mkdir(parents=True)
    (tmp_path / "data" / "Figures" / f"{figure_name}.json").write_text(
        json.dumps(definition), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError) as raised:
        getFigure(figure_name, [0, 0], ["Left", "Right"])

    assert "Left" in str(raised.value) and "Right" in str(raised.value)
    assert ("CriptDesc" if field == "CriptDesc" else field) in str(raised.value)
    assert "dancer 1" in str(raised.value)
    with pytest.raises(ValueError, match=field if field != "CriptDesc" else "CriptDesc"):
        FigureRepository(tmp_path / "data" / "Figures").validate_addons(
            figure_name, ["Left", "Right"], path="root"
        )

def test_instruction_replacement_changes_output_and_duration_bar_range():
    figure = getFigure("1cLT", [2, 0], ["B4", "E1c"])
    instructions = figure.getCrips(DanceFloor("turn", 3))
    assert figure.Bars == 4
    assert instructions == [
        "1 - 4: 2m turns left hand with 2w and ends facing 3w's position.",
        "1 - 4: 2w turns left hand with 2m and ends facing 1m's position.",
    ]
    shortened = getFigure("1cLT", [1, 0], ["B3"])
    assert shortened.getCrips(DanceFloor("turn", 1))[0].startswith("1 - 3:")



def test_migrated_dances_use_1cLT_with_duration_and_ending_addons():
    root = Path("data") / "Dances"
    for relative_path in (
        Path("Marries Wedding_all.json"),
        Path("subDances") / "Marries Wedding_Bar 1-8.json",
    ):
        data = json.loads((root / relative_path).read_text(encoding="utf-8"))
        selected = []

        def visit(value):
            if isinstance(value, list):
                if (
                    len(value) == 2
                    and isinstance(value[1], list)
                    and len(value[1]) == 2
                    and value[1][0] == "1cLT"
                ):
                    selected.append(value[1])
                for child in value:
                    visit(child)
            elif isinstance(value, dict):
                for child in value.values():
                    visit(child)

        visit(data)
        assert selected == [["1cLT", ["B4", "E1c"]]]
        assert "1cLT1c" not in json.dumps(data)

def test_two_serial_half_reels_with_b3_have_six_bar_duration():
    first = FigureOccurrence("half-1", "HLReelAU", (0, 0), ("B3",))
    second = FigureOccurrence("half-2", "HLReelAD", (0, 0), ("B3",))
    analysis = analyze_durations(GroupNode("root", "series", (first, second)), FigureRepository())
    assert analysis.node_durations == {"half-1": 3, "half-2": 3, "root": 6}
    assert analysis.duration == 6
    result = execute_document(
        DanceDocument(1, {}, GroupNode("root", "series", (first, second))),
        FloorState({}),
        FigureRepository(),
        figure_executor=lambda node, incoming, path, repository: incoming,
    )
    assert result.duration == 6
    figure_ranges = [record.bar_range for record in result.trace_records if record.kind == "figure"]
    assert figure_ranges == [(1, 3), (4, 6)]


def test_canonical_addon_validation_accepts_any_b_positive_integer_and_rejects_two():
    repository = FigureRepository()
    repository.validate_addons("HLReelAU", ["B3"], path="root")
    repository.validate_addons("HLReelAU", ["B8"], path="root")
    with pytest.raises(ValueError, match="B3.*B8|B8.*B3"):
        repository.validate_addons("HLReelAU", ["B3", "B8"], path="root")
    with pytest.raises(ValueError, match="B0|duration|addon"):
        repository.validate_addons("HLReelAU", ["B0"], path="root")


def test_addon_conflict_error_identifies_field_dancer_and_values(tmp_path, monkeypatch):
    definition = {
        "Name": "ConflictValues", "Version": 2, "Bars": 2,
        "StartPos": [[0, -1]], "EndPos": [[0, -1]],
        "CriptDesc": ["Dancer waits at StartPos"],
        "Addons": {
            "Left": {"Name": "Left", "Version": 1, "EndPos": [[1, 1]]},
            "Right": {"Name": "Right", "Version": 1, "EndPos": [[2, 2]]},
        },
    }
    (tmp_path / "data" / "Figures").mkdir(parents=True)
    (tmp_path / "data" / "Figures" / "ConflictValues.json").write_text(json.dumps(definition), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError) as raised:
        getFigure("ConflictValues", [0, 0], ["Left", "Right"])
    message = str(raised.value)
    assert "Left" in message and "Right" in message
    assert "EndPos" in message and "dancer 1" in message
    assert "[1, 1]" in message and "[2, 2]" in message
