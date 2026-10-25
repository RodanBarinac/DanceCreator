import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.domain.legacy_adapter import LegacyDanceAdapter


def test_duplicate_figure_references_receive_distinct_stable_ids():
    legacy = {
        "Name": "Repeated",
        "Version": 3,
        "FigureList": ["s", [
            [[1, 1], ["Turn", []]],
            [[2, 1], ["Turn", []]],
        ]],
    }

    document = LegacyDanceAdapter.from_data(legacy, reference_exists=lambda _: True)
    first, second = document.root.children

    assert isinstance(first, FigureOccurrence)
    assert isinstance(second, FigureOccurrence)
    assert first.figure_ref == second.figure_ref == "Turn"
    assert first.id != second.id
    restored = DanceDocument.from_json(document.to_json())
    assert restored.find_node(first.id) == first
    assert restored.find_node(second.id) == second


def test_canonical_recursive_document_round_trips_without_losing_metadata():
    document = DanceDocument(
        format_version=1,
        metadata={"name": "Nested", "shape": "3/4", "custom": {"source": "test"}},
        root=GroupNode(
            id="group-root",
            kind="series",
            children=(
                FigureOccurrence("occ-a", "A", (1, 2), ()),
                GroupNode(
                    "group-parallel",
                    "parallel",
                    (FigureOccurrence("occ-b", "B", (2, 1), ("Hands",)),),
                ),
            ),
        ),
        revision=7,
    )

    restored = DanceDocument.from_json(document.to_json())

    assert restored == document
    assert restored.metadata == document.metadata
    assert restored.find_node("occ-b").addons == ("Hands",)


def test_legacy_missing_reference_is_preserved_as_incomplete():
    legacy = {
        "Name": "Draft",
        "Version": 3,
        "FigureList": ["s", [[[1, 1], ["Missing", ["Addon"]]]]],
    }

    document = LegacyDanceAdapter.from_data(
        legacy,
        reference_exists=lambda figure_ref: figure_ref != "Missing",
    )

    assert document.incomplete is True
    assert document.unresolved_references == ("Missing",)
    occurrence = document.root.children[0]
    assert isinstance(occurrence, FigureOccurrence)
    assert occurrence.figure_ref == "Missing"
    assert occurrence.addons == ("Addon",)
    restored = DanceDocument.from_json(document.to_json())
    assert restored.incomplete is True
    assert restored.unresolved_references == ("Missing",)


def test_legacy_file_loading_does_not_rewrite_source(tmp_path):
    legacy = {
        "Name": "Legacy",
        "Desc": "Keep all source metadata",
        "Version": 3,
        "FigureList": ["s", [[[1, 1], "Known"]]],
    }
    source = tmp_path / "legacy-dance.json"
    original = json.dumps(legacy, separators=(",", ":"))
    source.write_text(original, encoding="utf-8")

    LegacyDanceAdapter.from_file(source, reference_exists=lambda _: True)

    assert source.read_text(encoding="utf-8") == original


def test_legacy_adapter_loads_real_nested_parallel_dance():
    from src.engine.figures.capabilities import FigureRepository

    dance_path = Path("data") / "Dances" / "Marries Wedding.json"
    repository = FigureRepository()

    document = LegacyDanceAdapter.from_file(
        dance_path,
        repository.figure_exists,
        get_definition=repository.get_legacy_definition,
    )

    assert document.incomplete is False
    assert document.root.kind == "series"
    assert any(
        isinstance(child, CompositeOccurrence)
        for child in document.root.children
    )
    composite = next(
        child for child in document.root.children if isinstance(child, CompositeOccurrence)
    )
    assert composite.root.kind in ("series", "parallel")
    assert isinstance(composite.root.children[0], (GroupNode, FigureOccurrence, CompositeOccurrence))
    assert len(
        {
            node.id
            for node in DanceDocument._walk(composite.root)
        }
    ) > 1


def test_composite_occurrence_embeds_children_and_round_trips_ids():
    composite_definition = {
        "Name": "Pair",
        "Version": 3,
        "FigureList": [
            "p",
            [
                [[0, 0], "Turn"],
                ["s", [[[1, 0], ["Turn", ["Hands"]]]]],
            ],
        ],
    }
    legacy = {
        "Name": "Composite dance",
        "Version": 3,
        "FigureList": ["s", [[[2, 1], ["Pair", []]]]],
    }

    document = LegacyDanceAdapter.from_data(
        legacy,
        reference_exists=lambda ref: ref == "Pair" or ref == "Turn",
        get_definition=lambda ref: composite_definition if ref == "Pair" else None,
    )
    composite = document.root.children[0]
    assert isinstance(composite, CompositeOccurrence)
    nested = composite.root.children[1]
    assert isinstance(nested, GroupNode)
    nested_figure = nested.children[0]
    assert isinstance(nested_figure, FigureOccurrence)
    assert nested_figure.anchor == (1, 0)

    restored = DanceDocument.from_json(document.to_json())

    assert restored == document
    assert restored.find_node(composite.id) == composite
    assert restored.find_node(nested_figure.id) == nested_figure


def test_unresolved_reference_inside_composite_preserves_incomplete_draft():
    composite_definition = {
        "Name": "Partial composite",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], "Missing"]]],
    }
    legacy = {
        "Name": "Draft with composite",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], "Partial composite"]]],
    }

    document = LegacyDanceAdapter.from_data(
        legacy,
        reference_exists=lambda ref: ref == "Partial composite",
        get_definition=lambda ref: composite_definition,
    )

    composite = document.root.children[0]
    assert isinstance(composite, CompositeOccurrence)
    assert isinstance(composite.root.children[0], FigureOccurrence)
    assert composite.root.children[0].figure_ref == "Missing"
    assert document.incomplete is True
    assert document.unresolved_references == ("Missing",)


def test_recursive_composite_reference_is_rejected():
    composite_definition = {
        "Name": "Loop",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], "Loop"]]],
    }

    with pytest.raises(ValueError, match="Recursive composite"):
        LegacyDanceAdapter.from_data(
            {
                "Name": "Loop parent",
                "Version": 3,
                "FigureList": ["s", [[[0, 0], "Loop"]]],
            },
            reference_exists=lambda _: True,
            get_definition=lambda _: composite_definition,
        )


def test_canonical_loader_rejects_inconsistent_draft_status():
    payload = {
        "formatVersion": 1,
        "metadata": {},
        "status": "complete",
        "unresolvedReferences": ["Missing"],
        "revision": 0,
        "root": {
            "type": "group",
            "id": "root",
            "kind": "series",
            "children": [],
        },
    }

    with pytest.raises(ValueError, match="unresolved"):
        DanceDocument.from_json(payload)


def test_canonical_loader_rejects_duplicate_node_ids():
    payload = {
        "formatVersion": 1,
        "metadata": {},
        "status": "complete",
        "unresolvedReferences": [],
        "revision": 0,
        "root": {
            "type": "group",
            "id": "duplicate",
            "kind": "series",
            "children": [
                {
                    "type": "figure",
                    "id": "duplicate",
                    "figureRef": "Known",
                    "anchor": [1, 1],
                    "addons": [],
                }
            ],
        },
    }

    with pytest.raises(ValueError, match="Duplicate dance node id"):
        DanceDocument.from_json(payload)


def test_find_node_uses_identity_not_current_tree_position():
    first = FigureOccurrence("occ-a", "A", (1, 1), ())
    second = FigureOccurrence("occ-b", "B", (1, 1), ())
    document = DanceDocument(
        1,
        {},
        GroupNode("root", "series", (first, second)),
    )
    reordered = replace(document, root=replace(document.root, children=(second, first)))

    assert reordered.find_node("occ-a") == first
