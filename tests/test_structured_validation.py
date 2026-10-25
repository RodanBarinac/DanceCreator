from copy import deepcopy
from types import SimpleNamespace

import pytest

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.figures.capabilities import FigureRepository
from src.engine.validation import validate_document
from src.engine.validation.errors import ValidationIssue


def _figure(node_id, figure_ref="1cWait", addons=(), anchor=(1, 0)):
    return FigureOccurrence(node_id, figure_ref, anchor, tuple(addons))


def _document(root, *, incomplete=False, unresolved=()):
    return DanceDocument(
        1,
        {"name": "validation test"},
        root,
        incomplete=incomplete,
        unresolved_references=tuple(unresolved),
    )


def _floor():
    return FloorState(
        {
            (1, -1): FloorEntry("M1", "male", (1, 1)),
            (1, 1): FloorEntry("W1", "female", (1, -1)),
            (0.5, -0.5): FloorEntry("M2", "male", (1, 2)),
            (1.5, 0.5): FloorEntry("W2", "female", (1, 0)),
            (2, 1): FloorEntry("M3", "male", (2, 2)),
            (0, -1): FloorEntry("W3", "female", (2, 0)),
        }
    )


class _Repository:
    def __init__(self, bars=None, existing=None):
        self.bars = bars or {}
        self.existing = existing

    def figure_exists(self, figure_ref):
        if self.existing is not None:
            return figure_ref in self.existing
        return figure_ref in self.bars

    def get_definition(self, figure_ref):
        if figure_ref not in self.bars:
            raise FileNotFoundError(figure_ref)
        return SimpleNamespace(bars=self.bars[figure_ref])


def test_valid_complete_document_has_no_errors_and_preserves_inputs():
    document = _document(GroupNode("root", "series", (_figure("wait"),)))
    initial = _floor()
    document_before = deepcopy(document.to_json())
    floor_before = deepcopy(dict(initial.positions))

    report = validate_document(document, initial, FigureRepository())

    assert report.errors == ()
    assert report.warnings == ()
    assert report.is_valid is True
    assert report.first_blocking is None
    assert document.to_json() == document_before
    assert dict(initial.positions) == floor_before


@pytest.mark.parametrize(
    ("incomplete", "unresolved"),
    [(False, ()), (True, ("Missing",))],
)
def test_missing_references_are_blocking_for_complete_and_incomplete_documents(
    incomplete, unresolved, monkeypatch
):
    from src.engine.validation import validator

    root = GroupNode(
        "tree",
        "series",
        (
            _figure("first", "Missing"),
            GroupNode("nested", "series", (_figure("second", "Missing"),)),
        ),
    )
    document = _document(
        root,
        incomplete=incomplete,
        unresolved=unresolved,
    )
    document_before = deepcopy(document.to_json())
    initial = _floor()
    floor_before = deepcopy(dict(initial.positions))
    monkeypatch.setattr(
        validator,
        "execute_document",
        lambda *args, **kwargs: pytest.fail("unresolved references must not execute"),
    )

    report = validate_document(document, initial, _Repository(existing=set()))

    assert report.is_valid is False
    assert report.first_blocking is report.errors[0]
    assert [error.code for error in report.errors] == [
        "reference_not_found",
        "reference_not_found",
    ]
    assert [error.path for error in report.errors] == [
        "root.children[0]",
        "root.children[1].children[0]",
    ]
    assert [error.occurrence_id for error in report.errors] == ["first", "second"]
    assert document.to_json() == document_before
    assert dict(initial.positions) == floor_before


@pytest.mark.parametrize(
    ("addons", "code", "path"),
    [
        (("Unknown",), "unsupported_addon", "root.children[0].addons[0]"),
        (("E2c", "E2c"), "invalid_addon_selection", "root.children[0].addons[1]"),
    ],
)
def test_addon_errors_keep_submitted_parameters_and_canonical_locations(
    addons, code, path, monkeypatch
):
    from src.engine.validation import validator

    document = _document(
        GroupNode("root", "series", (_figure("bad-addon", "H1DR", addons, (0, 0)),))
    )
    original = deepcopy(document.to_json())
    initial = _floor()
    floor_before = deepcopy(dict(initial.positions))
    monkeypatch.setattr(
        validator,
        "execute_document",
        lambda *args, **kwargs: pytest.fail("invalid capabilities must not execute"),
    )

    report = validate_document(document, initial, FigureRepository())

    assert report.is_valid is False
    error = report.first_blocking
    assert error.code == code
    assert error.path == path
    assert error.occurrence_id == "bad-addon"
    assert error.field == "addons"
    assert error.details["addons"] == tuple(addons)
    assert document.to_json() == original
    assert dict(initial.positions) == floor_before


def test_unequal_parallel_duration_is_structured_and_prevents_execution(monkeypatch):
    from src.engine.validation import validator

    document = _document(
        GroupNode(
            "root",
            "series",
            (
                GroupNode(
                    "duration-group",
                    "parallel",
                    (_figure("short", "One"), _figure("long", "Two")),
                ),
            ),
        )
    )
    initial = _floor()
    document_before = deepcopy(document.to_json())
    floor_before = deepcopy(dict(initial.positions))
    monkeypatch.setattr(
        validator,
        "execute_document",
        lambda *args, **kwargs: pytest.fail("duration errors must not execute"),
    )

    report = validate_document(
        document,
        initial,
        _Repository({"One": 1, "Two": 2}),
    )

    assert report.is_valid is False
    error = report.first_blocking
    assert error.code == "parallel_duration_mismatch"
    assert error.path == "root.children[0]"
    assert error.node_id == "duration-group"
    assert error.field == "duration"
    assert error.details["groupId"] == "duration-group"
    assert error.details["pathDurations"] == {"short": 1, "long": 2}
    assert document.to_json() == document_before
    assert dict(initial.positions) == floor_before


def test_addon_and_duration_errors_are_both_reported_before_execution(monkeypatch):
    from src.engine.validation import validator

    document = _document(
        GroupNode(
            "root",
            "series",
            (
                GroupNode(
                    "timing",
                    "parallel",
                    (
                        _figure("bad-addon", "H1DR", ("Unknown",)),
                        _figure("short", "1cWait"),
                    ),
                ),
            ),
        )
    )
    monkeypatch.setattr(
        validator,
        "execute_document",
        lambda *args, **kwargs: pytest.fail("invalid proposals must not execute"),
    )

    report = validate_document(document, _floor(), FigureRepository())

    assert [issue.code for issue in report.errors] == [
        "unsupported_addon",
        "parallel_duration_mismatch",
    ]
    assert report.first_blocking is report.errors[0]


def test_all_independent_parallel_duration_mismatches_are_reported():
    document = _document(
        GroupNode(
            "root",
            "series",
            (
                GroupNode(
                    "first-group",
                    "parallel",
                    (_figure("one", "One"), _figure("two", "Two")),
                ),
                GroupNode(
                    "second-group",
                    "parallel",
                    (_figure("three", "Three"), _figure("four", "Four")),
                ),
            ),
        )
    )

    report = validate_document(
        document,
        FloorState({}),
        _Repository({"One": 1, "Two": 2, "Three": 3, "Four": 4}),
    )

    assert [issue.code for issue in report.errors] == [
        "parallel_duration_mismatch",
        "parallel_duration_mismatch",
    ]
    assert [issue.node_id for issue in report.errors] == [
        "first-group",
        "second-group",
    ]


def test_parallel_conflict_reports_occurrences_positions_and_dancer_identity():
    document = _document(
        GroupNode(
            "root",
            "parallel",
            (
                _figure("left-occurrence", "H1DR", anchor=(0, 0)),
                _figure("right-occurrence", "H1DR", anchor=(0, 0)),
            ),
        )
    )
    initial = _floor()
    document_before = deepcopy(document.to_json())
    floor_before = deepcopy(dict(initial.positions))

    report = validate_document(document, initial, FigureRepository())

    assert report.is_valid is False
    error = next(
        item
        for item in report.errors
        if item.code == "parallel_conflict"
        and item.details["position"] == (2, 1)
    )
    assert error.node_id == "root"
    assert error.occurrence_id in {"left-occurrence", "right-occurrence"}
    assert error.path in {"root.children[0]", "root.children[1]"}
    assert error.details["groupId"] == "root"
    assert error.details["position"] == (2, 1)
    writes = error.details["competingWrites"]
    assert [write["occurrenceId"] for write in writes] == [
        "left-occurrence",
        "right-occurrence",
    ]
    assert [write["dancer"]["name"] for write in writes] == ["W3", "W3"]
    assert [write["to"] for write in writes] == [(2, 1), (2, 1)]
    assert document.to_json() == document_before
    assert dict(initial.positions) == floor_before


def test_nested_parallel_conflict_uses_canonical_indexed_path():
    document = _document(
        GroupNode(
            "root",
            "series",
            (
                GroupNode(
                    "outer",
                    "series",
                    (
                        GroupNode(
                            "nested",
                            "parallel",
                            (
                                _figure("nested-left", "H1DR", anchor=(0, 0)),
                                _figure("nested-right", "H1DR", anchor=(0, 0)),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )

    report = validate_document(document, _floor(), FigureRepository())

    error = next(item for item in report.errors if item.code == "parallel_conflict")
    assert error.path == "root.children[0].children[0].children[0]"
    assert error.node_id == "nested"
    assert error.details["groupId"] == "nested"
    assert {write["occurrenceId"] for write in error.details["competingWrites"]} == {
        "nested-left",
        "nested-right",
    }


def test_malformed_top_level_input_returns_structural_report():
    report = validate_document({"not": "a DanceDocument"}, _floor(), FigureRepository())

    assert report.is_valid is False
    assert report.first_blocking is report.errors[0]
    assert report.errors[0].code == "invalid_document_structure"
    assert report.errors[0].path == "document"


@pytest.mark.parametrize("coordinate", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_anchors_are_structural_errors(coordinate):
    document = _document(
        GroupNode("root", "series", (_figure("bad-anchor", anchor=(coordinate, 1)),))
    )

    report = validate_document(document, _floor(), FigureRepository())

    assert report.is_valid is False
    assert report.first_blocking.code == "invalid_document_structure"
    assert report.first_blocking.path == "root.children[0]"
    assert report.first_blocking.occurrence_id == "bad-anchor"


def test_composite_occurrence_must_resolve_to_a_composite_definition():
    document = _document(
        GroupNode(
            "root",
            "series",
            (
                CompositeOccurrence(
                    "composite",
                    "1cWait",
                    (0, 0),
                    (),
                    GroupNode("embedded", "series", ()),
                ),
            ),
        )
    )

    report = validate_document(document, FloorState({}), FigureRepository())

    assert report.is_valid is False
    assert report.first_blocking.code == "invalid_composite_reference"
    assert report.first_blocking.path == "root.children[0]"
    assert report.first_blocking.occurrence_id == "composite"


def test_non_empty_composite_addons_are_rejected_as_unsupported():
    document = _document(
        GroupNode(
            "root",
            "series",
            (
                CompositeOccurrence(
                    "composite",
                    "Marries Wedding_Bar 1-8",
                    (0, 0),
                    ("OuterAddon",),
                    GroupNode("embedded", "series", ()),
                ),
            ),
        )
    )

    report = validate_document(document, FloorState({}), FigureRepository())

    assert report.is_valid is False
    assert report.first_blocking.code == "unsupported_addon"
    assert report.first_blocking.path == "root.children[0].addons"
    assert report.first_blocking.occurrence_id == "composite"


def test_fallback_capability_validation_checks_empty_addon_combinations():
    class _CombinationRepository:
        def figure_exists(self, figure_ref):
            return figure_ref == "Choice"

        def get_definition(self, figure_ref):
            return SimpleNamespace(
                bars=2,
                valid_addons=(),
                allowed_addon_combinations=(frozenset({"A"}),),
            )

    document = _document(
        GroupNode("root", "series", (_figure("choice", "Choice"),))
    )

    report = validate_document(document, FloorState({}), _CombinationRepository())

    assert report.is_valid is False
    assert report.first_blocking.code == "invalid_addon_combination"
    assert report.first_blocking.path == "root.children[0].addons"


def test_validation_issue_details_cannot_be_mutated_after_creation():
    issue = ValidationIssue(
        code="invalid",
        severity="error",
        path="root",
        node_id="root",
        occurrence_id=None,
        field="structure",
        message="Invalid.",
        details={"nested": [{"value": "original"}]},
    )

    with pytest.raises(TypeError):
        issue.details["new"] = "value"
    with pytest.raises(TypeError):
        issue.details["nested"][0]["value"] = "changed"

    serialized = issue.to_dict()
    assert serialized["details"] == {"nested": [{"value": "original"}]}
    serialized["details"]["nested"][0]["value"] = "changed"
    assert issue.to_dict()["details"]["nested"][0]["value"] == "original"


def test_report_serialization_and_first_blocking_are_deterministic():
    document = _document(
        GroupNode(
            "root",
            "series",
            (_figure("first", "Missing"), _figure("second", "Missing")),
        ),
        incomplete=True,
        unresolved=("Missing",),
    )

    first = validate_document(document, _floor(), _Repository(existing=set()))
    second = validate_document(document, _floor(), _Repository(existing=set()))

    assert first.errors == second.errors
    assert first.first_blocking == first.errors[0]
    assert first.is_valid is False
    assert first.warnings == ()
    assert first.errors[0].to_dict() == {
        "code": "reference_not_found",
        "severity": "error",
        "path": "root.children[0]",
        "nodeId": "first",
        "occurrenceId": "first",
        "field": "figureRef",
        "message": "Figure reference 'Missing' could not be resolved.",
        "details": {"figureRef": "Missing"},
    }
