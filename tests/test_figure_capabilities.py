import json
from pathlib import Path

import pytest

from src.engine.domain.dance_model import FigureOccurrence
from src.engine.figures.capabilities import AddonValidationError, FigureRepository


def write_figure(directory, definition):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{definition['Name']}.json"
    path.write_text(json.dumps(definition), encoding="utf-8")
    return path


def figure_definition(**overrides):
    definition = {
        "Name": "TestFigure",
        "Desc": "A test figure",
        "Version": 2,
        "Bars": 4,
        "Formation": "reel",
        "Addons": {
            "A": {"Name": "A", "Desc": "Addon A", "EndPos": [[1, 1]]},
            "B": {"Name": "B", "Desc": "Addon B", "EndFacing": [[1, 0]]},
        },
    }
    definition.update(overrides)
    return definition


def test_capabilities_expose_exact_legacy_addon_list_and_metadata():
    repository = FigureRepository(Path("data") / "Figures")

    capabilities = repository.get_capabilities("H1DR")

    assert capabilities.figure_ref == "H1DR"
    assert capabilities.bars == 4
    assert capabilities.formation == "reel"
    assert capabilities.capability_version == 1
    assert capabilities.supports_preview is True
    assert capabilities.duration_addon_pattern == "B<n>"
    assert [addon["name"] for addon in capabilities.valid_addons] == ["E2c", "ELA"]
    assert capabilities.valid_addons[0]["description"] == "End facing 2 corner"
    assert "EndFacing" in capabilities.valid_addons[0]["parameters"]


def test_repository_resolves_legacy_composite_from_subdance_directory():
    repository = FigureRepository()

    definition = repository.get_legacy_definition("Marries Wedding_Bar 1-8")

    assert definition["Version"] == 3
    assert "FigureList" in definition
    assert repository.figure_exists("Marries Wedding_Bar 1-8") is True
    assert repository.figure_exists("FigureThatDoesNotExist") is False


def test_all_bundled_atomic_figure_definitions_have_capabilities():
    figure_directory = Path("data") / "Figures"
    repository = FigureRepository(figure_directory)

    definitions = [
        (path.stem, json.loads(path.read_text(encoding="utf-8-sig")))
        for path in figure_directory.glob("*.json")
    ]
    atomic_refs = [
        figure_ref
        for figure_ref, definition in definitions
        if definition.get("Version") == 2
    ]

    assert atomic_refs
    for figure_ref in atomic_refs:
        capabilities = repository.get_capabilities(figure_ref)
        assert capabilities.figure_ref == figure_ref


def test_addon_selections_are_owned_by_each_occurrence(tmp_path):
    write_figure(tmp_path, figure_definition())
    repository = FigureRepository(tmp_path)
    first = FigureOccurrence("occ-a", "TestFigure", (1, 1), ("A",))
    second = FigureOccurrence("occ-b", "TestFigure", (2, 1), ("B",))

    assert first.addons == ("A",)
    assert second.addons == ("B",)
    assert [item["name"] for item in repository.get_capabilities("TestFigure").valid_addons] == [
        "A",
        "B",
    ]


def test_invalid_addon_reports_occurrence_and_parameter_path(tmp_path):
    write_figure(tmp_path, figure_definition())
    repository = FigureRepository(tmp_path)

    with pytest.raises(AddonValidationError) as raised:
        repository.validate_addons(
            "TestFigure",
            ["Unknown"],
            path="root.children[0]",
            occurrence_id="occ-1",
        )

    assert raised.value.code == "unsupported_addon"
    assert raised.value.path == "root.children[0].addons[0]"
    assert raised.value.figure_ref == "TestFigure"
    assert raised.value.occurrence_id == "occ-1"
    assert raised.value.addons == ("Unknown",)


def test_failed_combination_keeps_selected_addons_and_reports_path(tmp_path):
    write_figure(
        tmp_path,
        figure_definition(
            CapabilityVersion=3,
            AddonCombinationValidator={
                "allowedCombinations": [[], ["A"], ["B"]]
            },
        ),
    )
    repository = FigureRepository(tmp_path)
    selection = ["A", "B"]

    with pytest.raises(AddonValidationError) as raised:
        repository.validate_addons(
            "TestFigure",
            selection,
            path="root.children[2]",
            occurrence_id="occ-3",
        )

    assert selection == ["A", "B"]
    assert raised.value.code == "invalid_addon_combination"
    assert raised.value.path == "root.children[2].addons"
    assert raised.value.occurrence_id == "occ-3"
    assert raised.value.addons == ("A", "B")


def test_allowed_combinations_are_order_insensitive(tmp_path):
    write_figure(
        tmp_path,
        figure_definition(
            CapabilityVersion=3,
            AddonCombinationValidator={
                "allowedCombinations": [[], ["A", "B"]]
            },
        ),
    )
    repository = FigureRepository(tmp_path)
    selection = ["B", "A"]

    repository.validate_addons("TestFigure", selection, path="root")

    assert selection == ["B", "A"]


def test_duplicate_addon_selection_is_rejected_without_rewriting(tmp_path):
    write_figure(
        tmp_path,
        figure_definition(
            AddonCombinationValidator={"allowedCombinations": [["A"]]}
        ),
    )
    repository = FigureRepository(tmp_path)
    selection = ["A", "A"]

    with pytest.raises(AddonValidationError) as raised:
        repository.validate_addons("TestFigure", selection, path="root")

    assert raised.value.code == "invalid_addon_selection"
    assert raised.value.path == "root.addons[1]"
    assert raised.value.addons == ("A", "A")
    assert selection == ["A", "A"]


def test_legacy_addon_name_array_is_normalized_as_capabilities(tmp_path):
    write_figure(tmp_path, figure_definition(Addons=["A", "B"]))

    capabilities = FigureRepository(tmp_path).get_capabilities("TestFigure")

    assert [addon["name"] for addon in capabilities.valid_addons] == ["A", "B"]
    assert all(addon["parameters"] == {} for addon in capabilities.valid_addons)


def test_mutating_returned_capabilities_does_not_change_repository_metadata(tmp_path):
    write_figure(tmp_path, figure_definition())
    repository = FigureRepository(tmp_path)
    first = repository.get_capabilities("TestFigure")
    first.valid_addons[0]["parameters"]["EndPos"][0][0] = 99

    second = repository.get_capabilities("TestFigure")

    assert second.valid_addons[0]["parameters"]["EndPos"] == [[1, 1]]


def test_addon_combinations_default_to_individual_capability_checks(tmp_path):
    write_figure(tmp_path, figure_definition())
    repository = FigureRepository(tmp_path)

    repository.validate_addons("TestFigure", ["A", "B"], path="root")


def test_invalid_capability_version_is_rejected(tmp_path):
    write_figure(tmp_path, figure_definition(CapabilityVersion=0))
    repository = FigureRepository(tmp_path)

    with pytest.raises(ValueError, match="CapabilityVersion"):
        repository.get_capabilities("TestFigure")


def test_figure_reference_cannot_escape_repository_directory(tmp_path):
    repository = FigureRepository(tmp_path)

    with pytest.raises(ValueError, match="figure reference"):
        repository.get_definition("..\\outside")


def test_figure_level_legacy_faceing_is_rejected_by_definition_and_legacy_loader(tmp_path):
    write_figure(tmp_path, figure_definition(Faceing=[[1, 0]]))
    repository = FigureRepository(tmp_path)

    for load in (repository.get_definition, repository.get_legacy_definition,
                 repository.get_capabilities):
        with pytest.raises(ValueError, match="Faceing.*EndFacing"):
            load("TestFigure")


def test_addon_level_legacy_faceing_is_rejected_by_definition_and_legacy_loader(tmp_path):
    definition = figure_definition()
    definition["Addons"]["B"] = {"Name": "B", "Desc": "Addon B", "Faceing": [[1, 0]]}
    write_figure(tmp_path, definition)
    repository = FigureRepository(tmp_path)

    for load in (repository.get_definition, repository.get_legacy_definition,
                 repository.get_capabilities):
        with pytest.raises(ValueError, match="Faceing.*'B'.*EndFacing"):
            load("TestFigure")


def test_generic_facing_prose_is_not_rejected(tmp_path):
    definition = figure_definition(Desc="Dancers end facing up, no Faceing typo here")
    definition["Addons"]["A"]["Desc"] = "End facing 2 corner"
    write_figure(tmp_path, definition)
    repository = FigureRepository(tmp_path)

    assert repository.get_definition("TestFigure").bars == 4
    assert repository.get_legacy_definition("TestFigure")["Name"] == "TestFigure"
