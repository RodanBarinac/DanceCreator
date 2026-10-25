"""Regression tests for the centered dance grid and composable turn addons."""

import json
from pathlib import Path

import pytest

from src.engine.models import DanceFloor
from src.engine.models.Dance import getFigure
from src.engine.validators.DancefloorContractValidator import DancefloorSerializer


def test_default_dancers_use_centered_grid_and_face_opposite_side():
    floor = DanceFloor.DanceFloor("centered", 2)

    assert set(floor.DanceFloorMap) == {(1, -1), (1, 1), (2, -1), (2, 1)}
    assert floor.DanceFloorMap[(1, -1)][1] == [1, 1]
    assert floor.DanceFloorMap[(1, 1)][1] == [1, -1]
    assert floor.PosNamebyPos((1, -1)) == "1m's position"
    assert floor.PosNamebyPos((1, 0)) == "between 1c's position"
    assert "Men(-1)" in str(floor) and "Between(0)" in str(floor) and "Lady(+1)" in str(floor)


def test_floor_serializer_uses_centered_side_keys_and_default_facing():
    floor = DanceFloor.DanceFloor("centered", 1)
    serialized = DancefloorSerializer.serialize_dancefloor(
        "centered", 1, 0, floor.DanceFloorMap
    )

    assert serialized["positions"]["1m"]["coord"] == [1, -1]
    assert serialized["positions"]["1m"]["facing"] == [1, 1]
    assert serialized["positions"]["1w"]["coord"] == [1, 1]
    assert serialized["positions"]["1w"]["facing"] == [1, -1]


def test_one_couple_left_turn_addons_override_duration_ending_and_text():
    figure = getFigure("1cLT", [2, 0], ["B4", "E1c"])

    assert figure.Bars == 4
    assert figure.StartPos == [(0, -1), (0, 1)]
    assert figure.EndPos == [[0.5, 0.5], [-0.5, -0.5]]
    assert figure.EndFacing == [[1, 1], [-1, -1]]

    floor = DanceFloor.DanceFloor("turn", 3)
    instructions = figure.getCrips(floor)
    assert instructions == [
        "1 - 4: 2m turns left hand with 2w and ends facing 3w's position.",
        "1 - 4: 2w turns left hand with 2m and ends facing 1m's position.",
    ]

    migrated_floor = figure.DanceMove(DanceFloor.DanceFloor("turn", 3))
    actual = sorted(
        (list(position), dancer.name, dancer.gender, list(facing) if facing else [])
        for position, (dancer, facing) in migrated_floor.DanceFloorMap.items()
    )
    expected = [
        ([1.5, -0.5], "2w", "female", [1, -1]),
        ([2.5, 0.5], "2m", "male", [3, 1]),
    ]
    assert actual == expected


def test_grid_before_state_fixture_captures_genuine_three_couple_run():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "design_grid_before_state.json").read_text(
            encoding="utf-8"
        )
    )
    baseline = next(
        entry
        for entry in fixture["executions"]
        if entry["dance"] == "Marries Wedding_all.json" and entry["couples"] == 3
    )

    assert baseline["bar_count"] == 40
    assert len(baseline["floor"]) == 6
    assert len(baseline["instructions"]) == 9
    assert baseline["floor"][0]["position"] == [1, 1]
    assert "1m turns left hand with 1w" in baseline["instructions"][1][0][0]


def test_grid_baseline_records_unsupported_cases_without_fabricated_states():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "design_grid_before_state.json").read_text(
            encoding="utf-8"
        )
    )
    executions = fixture["executions"]
    supported = [entry for entry in executions if "floor" in entry]
    unsupported = [entry for entry in executions if "floor" not in entry]

    assert len(executions) == 21
    assert {(entry["dance"], entry["couples"]) for entry in supported} == {
        ("Marries Wedding.json", 3),
        ("Marries Wedding_all.json", 3),
    }
    assert len(unsupported) == 19
    assert all(
        any(key in entry for key in ("execution_error", "instructions_error", "model_bars_error"))
        for entry in unsupported
    )


def _flatten_instruction_text(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [line for child in value for line in _flatten_instruction_text(child)]
    return []


@pytest.mark.parametrize('dance_name', ['Marries Wedding.json', 'Marries Wedding_all.json'])
def test_three_couple_dance_execution_matches_captured_grid_invariant(dance_name):
    from src.engine.models.Dance import getDance

    fixture = json.loads(
        (Path(__file__).parent / 'fixtures' / 'design_grid_before_state.json').read_text(
            encoding='utf-8'
        )
    )
    baseline = next(
        entry for entry in fixture['executions']
        if entry['dance'] == dance_name and entry['couples'] == 3
    )
    dance = getDance(dance_name)
    initial_floor = DanceFloor.DanceFloor(dance_name, 3)

    instructions = _flatten_instruction_text(dance.getCrips(initial_floor))
    final_floor = dance.DanceMove(initial_floor)
    actual_positions = sorted(
        (
            [position[0], position[1]],
            dancer.name,
            dancer.gender,
            list(facing) if isinstance(facing, (tuple, list)) else facing,
        )
        for position, (dancer, facing) in final_floor.DanceFloorMap.items()
    )
    expected_positions = sorted(
        (
            [entry['position'][0], entry['position'][1] - 2],
            entry['dancer'],
            entry['gender'],
            [entry['facing'][0], entry['facing'][1] - 2] if entry['facing'] else [],
        )
        for entry in baseline['floor']
    )

    assert final_floor.AktBar - 1 == baseline['bar_count']
    assert instructions == _flatten_instruction_text(baseline['instructions'])
    assert actual_positions == expected_positions


def test_one_couple_left_turn_base_partner_offsets_are_migrated():
    root = Path(__file__).resolve().parents[1]
    figure = json.loads((root / 'data' / 'Figures' / '1cLT.json').read_text(encoding='utf-8'))

    assert figure['StartPos'] == [[0, -1], [0, 1]]
    assert figure['EndPos'] == [[0, -1], [0, 1]]
    assert figure['Partner'] == [[0, -1], [0, 1]]
    assert 'Anchor' not in figure  # The loader ignores the old field.
    assert figure['Addons']['E1c']['EndPos'] == [[0.5, 0.5], [-0.5, -0.5]]


def test_only_canonical_data_folders_remain_and_variant_is_removed():
    root = Path(__file__).resolve().parents[1]
    assert not (root / 'Figures').exists()
    assert not (root / 'Dances').exists()
    assert not (root / 'data' / 'Figures' / '1cLT1c.json').exists()


def test_figure_and_addon_data_uses_facing_spelling_only():
    root = Path(__file__).resolve().parents[1]

    def assert_no_legacy_key(value, path):
        if isinstance(value, dict):
            assert 'Faceing' not in value, path
            for key, child in value.items():
                assert_no_legacy_key(child, f'{path}.{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value):
                assert_no_legacy_key(child, f'{path}[{index}]')

    for path in (root / 'data' / 'Figures').glob('*.json'):
        assert_no_legacy_key(json.loads(path.read_text(encoding='utf-8')), str(path))


def test_simple_figure_loader_does_not_read_root_fallback(tmp_path, monkeypatch):
    from src.engine.figures.SimpleFigure import SimpleFigure

    monkeypatch.chdir(tmp_path)
    figures = tmp_path / 'Figures'
    figures.mkdir()
    (figures / 'Legacy.json').write_text(
        json.dumps({'Name': 'Legacy', 'Version': 2, 'Bars': 1, 'StartPos': [], 'EndPos': []}),
        encoding='utf-8',
    )

    with pytest.raises(FileNotFoundError):
        SimpleFigure('Legacy')



def test_complex_figure_loader_does_not_read_root_fallback(tmp_path, monkeypatch):
    from src.engine.figures.ComplexFigure import ComplexFigure

    monkeypatch.chdir(tmp_path)
    figures = tmp_path / 'Figures'
    figures.mkdir()
    (figures / 'LegacyComposite.json').write_text(
        json.dumps({'Name': 'LegacyComposite', 'Version': 3, 'FigureList': ['s', []]}),
        encoding='utf-8',
    )

    with pytest.raises(FileNotFoundError):
        ComplexFigure('LegacyComposite').loadFigure()


def test_gui_figure_resolvers_do_not_read_root_fallback(tmp_path, monkeypatch):
    import GUI_DanceCreator_App as app_module

    monkeypatch.chdir(tmp_path)
    figures = tmp_path / 'Figures'
    figures.mkdir()
    (figures / 'Legacy.json').write_text(
        json.dumps({'Name': 'Legacy', 'Version': 2, 'Bars': 1}),
        encoding='utf-8',
    )
    monkeypatch.setattr(app_module, 'FIGURES_DIR', str(tmp_path / 'data' / 'Figures'))
    monkeypatch.setattr(app_module, 'DANCES_DIR', str(tmp_path / 'data' / 'Dances'))

    assert app_module._figure_detail_path('Legacy') is None
    with pytest.raises(FileNotFoundError):
        app_module._resolve_json_path('Legacy', ['Figures'])


@pytest.mark.parametrize('old_field_location', ['figure', 'addon'])
def test_simple_figure_loader_rejects_faceing_spelling(tmp_path, monkeypatch, old_field_location):
    from src.engine.figures.SimpleFigure import SimpleFigure

    monkeypatch.chdir(tmp_path)
    figures = tmp_path / 'data' / 'Figures'
    figures.mkdir(parents=True)
    definition = {
        'Name': 'LegacySpelling',
        'Version': 2,
        'Bars': 2,
        'StartPos': [[0, -1]],
        'EndPos': [[0, -1]],
        'Partner': [[]],
        'CriptDesc': ['wait'],
        'Addons': {},
    }
    if old_field_location == 'figure':
        definition['Faceing'] = [[0, 1]]
    else:
        definition['Addons']['Legacy'] = {'Name': 'Legacy', 'Version': 1, 'Faceing': [[0, 1]]}
    (figures / 'LegacySpelling.json').write_text(json.dumps(definition), encoding='utf-8')

    selected = ['Legacy'] if old_field_location == 'addon' else []
    with pytest.raises(ValueError, match='Faceing'):
        SimpleFigure('LegacySpelling', Addons=selected)


def test_floor_serializer_defaults_facing_across_centered_grid():
    floor = DanceFloor.DanceFloor("centered", 1)
    for position in floor.DanceFloorMap.values():
        position[1] = None

    serialized = DancefloorSerializer.serialize_dancefloor(
        "centered", 1, 0, floor.DanceFloorMap
    )

    assert serialized["positions"]["1m"]["facing"] == [1, 1]
    assert serialized["positions"]["1w"]["facing"] == [1, -1]


def test_floor_contract_allows_negative_columns_but_keeps_rows_one_based():
    from src.engine.validators.DancefloorContractValidator import (
        DancefloorContractError,
        DancefloorValidator,
    )

    validator = DancefloorValidator()
    floor = {
        'name': 'centered',
        'couples': 1,
        'tick': 0,
        'positions': {
            '1m': {
                'dancer': {'name': '1m', 'gender': 'M'},
                'coord': [1, -1],
                'facing': [1, 1],
            },
            '1w': {
                'dancer': {'name': '1w', 'gender': 'F'},
                'coord': [1, 1],
                'facing': [1, -1],
            },
        },
    }

    validator.validate(floor)
    floor['positions']['1m']['coord'][0] = 0
    with pytest.raises(DancefloorContractError):
        validator.validate(floor)
