from types import SimpleNamespace

import pytest

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.execution.duration import (
    ExecutionError,
    ParallelDurationError,
    analyze_durations,
)
from src.engine.execution.executor import _ExecutionContext, execute_document, execute_node


def _figure(node_id, figure_ref=None):
    return FigureOccurrence(node_id, figure_ref or node_id, (0, 0), ())


def _document(root):
    return DanceDocument(1, {}, root)


class _Repository:
    def __init__(self, bars):
        self.bars = bars

    def get_definition(self, figure_ref):
        if figure_ref not in self.bars:
            raise KeyError(figure_ref)
        return SimpleNamespace(bars=self.bars[figure_ref])


def _identity_executor(*args):
    return args[1]


def test_series_duration_sums_nested_figures_groups_and_composites():
    root = GroupNode(
        "root",
        "series",
        (
            _figure("first", "A"),
            GroupNode("nested", "series", (_figure("second", "B"), _figure("third", "C"))),
            CompositeOccurrence(
                "composite",
                "Composite",
                (4, 7),
                (),
                GroupNode(
                    "composite-root",
                    "series",
                    (
                        _figure("fourth", "D"),
                        GroupNode("composite-nested", "series", (_figure("fifth", "E"),)),
                    ),
                ),
            ),
        ),
    )

    result = execute_document(
        _document(root),
        FloorState({}),
        _Repository({"A": 2, "B": 3, "C": 4, "D": 5, "E": 6}),
        figure_executor=_identity_executor,
    )

    assert result.duration == 20


def test_equal_duration_parallel_paths_are_accepted():
    root = GroupNode(
        "parallel",
        "parallel",
        (
            _figure("left", "TwoBars"),
            GroupNode("right-series", "series", (_figure("right-a", "One"), _figure("right-b", "One"))),
        ),
    )

    result = execute_document(
        _document(root),
        FloorState({}),
        _Repository({"TwoBars": 2, "One": 1}),
        figure_executor=_identity_executor,
    )

    assert result.duration == 2


def test_each_node_execution_reports_its_preflight_duration():
    root = GroupNode(
        "root",
        "series",
        (
            _figure("first", "One"),
            GroupNode(
                "parallel",
                "parallel",
                (_figure("left", "Two"), _figure("right", "Two")),
            ),
            CompositeOccurrence(
                "composite",
                "Composite",
                (0, 0),
                (),
                GroupNode("composite-root", "series", (_figure("inside", "Three"),)),
            ),
        ),
    )
    repository = _Repository({"One": 1, "Two": 2, "Three": 3})
    analysis = analyze_durations(root, repository)
    context = _ExecutionContext(repository, _identity_executor, analysis.node_durations)

    for node in DanceDocument._walk(root):
        execution = execute_node(node, FloorState({}), (), context)
        assert execution.duration == analysis.node_durations[node.id]


def test_unequal_nested_parallel_paths_reject_before_any_figure_executes():
    initial = FloorState({(1, 1): FloorEntry("M1", "male", (1, 3))})
    calls = []

    def should_not_execute(*args):
        calls.append(args[0].id)
        return args[1]

    root = GroupNode(
        "root",
        "series",
        (
            GroupNode(
                "parallel",
                "parallel",
                (
                    GroupNode("short-path", "series", (_figure("short", "Two"),)),
                    GroupNode(
                        "long-path",
                        "series",
                        (_figure("long-a", "Two"), _figure("long-b", "Three")),
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(ParallelDurationError) as raised:
        execute_document(
            _document(root),
            initial,
            _Repository({"Two": 2, "Three": 3}),
            figure_executor=should_not_execute,
        )

    error = raised.value
    assert error.code == "parallel_duration_mismatch"
    assert error.group_id == "parallel"
    assert error.path == ("root", "parallel")
    assert error.path_durations == {"short-path": 2, "long-path": 5}
    assert "short-path=2" in str(error)
    assert "long-path=5" in str(error)
    assert calls == []
    assert initial.positions[(1, 1)].dancer_name == "M1"


def test_explicit_wait_resolves_mismatch_only_when_bars_make_paths_equal():
    root = GroupNode(
        "parallel",
        "parallel",
        (
            GroupNode(
                "padded",
                "series",
                (_figure("move", "Two"), _figure("wait", "1cWait")),
            ),
            _figure("other", "Three"),
        ),
    )
    result = execute_document(
        _document(root),
        FloorState({}),
        _Repository({"Two": 2, "1cWait": 1, "Three": 3}),
        figure_executor=_identity_executor,
    )
    assert result.duration == 3

    unpadded_enough = GroupNode(
        "parallel",
        "parallel",
        (
            GroupNode("padded", "series", (_figure("move", "Two"), _figure("wait", "1pWait"))),
            _figure("other", "Three"),
        ),
    )
    with pytest.raises(ParallelDurationError) as raised:
        execute_document(
            _document(unpadded_enough),
            FloorState({}),
            _Repository({"Two": 2, "1pWait": 2, "Three": 3}),
            figure_executor=_identity_executor,
        )
    assert raised.value.code == "parallel_duration_mismatch"
    assert raised.value.path_durations == {"padded": 4, "other": 3}


def test_duration_validation_never_pads_and_failure_has_no_result():
    root = GroupNode(
        "parallel",
        "parallel",
        (_figure("short", "One"), _figure("long", "Three")),
    )
    initial = FloorState({})

    with pytest.raises(ParallelDurationError) as raised:
        execute_document(
            _document(root),
            initial,
            _Repository({"One": 1, "Three": 3}),
            figure_executor=_identity_executor,
        )

    assert raised.value.code == "parallel_duration_mismatch"
    assert initial == FloorState({})
    assert not hasattr(raised.value, "partial_result")


def test_empty_and_single_child_groups_have_natural_durations():
    root = GroupNode(
        "root",
        "series",
        (
            GroupNode("empty-series", "series", ()),
            GroupNode("empty-parallel", "parallel", ()),
            GroupNode("single-parallel", "parallel", (_figure("only", "One"),)),
        ),
    )

    result = execute_document(
        _document(root),
        FloorState({}),
        _Repository({"One": 4}),
        figure_executor=_identity_executor,
    )

    assert result.duration == 4


def test_unknown_or_unsupported_figure_definitions_propagate():
    document = _document(GroupNode("root", "series", (_figure("missing", "Missing"),)))

    with pytest.raises(KeyError, match="Missing"):
        execute_document(
            document,
            FloorState({}),
            _Repository({}),
            figure_executor=_identity_executor,
        )
    with pytest.raises(ValueError, match="positive integer"):
        execute_document(
            document,
            FloorState({}),
            _Repository({"Missing": 0}),
            figure_executor=_identity_executor,
        )


def test_missing_repository_cannot_bypass_parallel_duration_validation():
    calls = []

    def should_not_execute(*args):
        calls.append(args[0].id)
        return args[1]

    root = GroupNode(
        "parallel",
        "parallel",
        (_figure("left", "One"), _figure("right", "Two")),
    )

    with pytest.raises(ExecutionError) as raised:
        execute_document(
            _document(root),
            FloorState({}),
            repository=None,
            figure_executor=should_not_execute,
        )

    assert raised.value.code == "duration_unavailable"
    assert raised.value.node_id == "left"
    assert calls == []


def test_addon_bars_override_drives_figure_and_parallel_durations():
    from src.engine.figures.capabilities import FigureRepository

    root = GroupNode(
        "parallel",
        "parallel",
        (
            _figure("turned", "1cLT"),
            GroupNode(
                "four-bar-path",
                "series",
                (_figure("first-two", "1cRT"), _figure("second-two", "1cRT")),
            ),
        ),
    )
    turned = FigureOccurrence("turned", "1cLT", (2, 0), ("B4", "E1c"))
    root = GroupNode(
        "parallel",
        "parallel",
        (
            turned,
            GroupNode(
                "four-bar-path",
                "series",
                (_figure("first-two", "1cRT"), _figure("second-two", "1cRT")),
            ),
        ),
    )
    repository = FigureRepository()

    analysis = analyze_durations(root, repository)
    result = execute_document(
        _document(root),
        FloorState({}),
        repository,
        figure_executor=_identity_executor,
    )

    assert analysis.node_durations["turned"] == 4
    assert analysis.node_durations["parallel"] == 4
    assert result.duration == 4
    figure_trace = next(record for record in result.trace_records if record.node_id == "turned")
    assert figure_trace.bar_range == (1, 4)
