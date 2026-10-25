from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.execution.combine import (
    FloorEntry,
    FloorState,
    ParallelWriteConflict,
)
from src.engine.execution.executor import FigureExecutionError, execute_document


def floor():
    return FloorState(
        {
            (1, -1): FloorEntry("M1", "male", (1, 1)),
            (1, 1): FloorEntry("W1", "female", (1, -1)),
            (2, -1): FloorEntry("M2", "male", (2, 1)),
            (2, 1): FloorEntry("W2", "female", (2, -1)),
        }
    )


def occurrence(node_id, figure_ref=None):
    return FigureOccurrence(node_id, figure_ref or node_id, (0, 0), ())


def document(root):
    return DanceDocument(1, {}, root)


class _TestRepository:
    def get_definition(self, figure_ref):
        return SimpleNamespace(bars=2)


def test_parallel_children_receive_same_immutable_input_and_merge_disjoint_changes():
    initial = floor()
    observed_inputs = []

    def execute_figure(node, incoming, path, repository):
        observed_inputs.append((node.id, incoming))
        positions = dict(incoming.positions)
        if node.id == "move-man":
            positions.pop((1, -1))
            positions[(2, 2)] = incoming.positions[(1, -1)]
        else:
            positions.pop((1, 1))
            positions[(2, 4)] = incoming.positions[(1, 1)]
        return FloorState(positions)

    dance = document(
        GroupNode(
            "root",
            "parallel",
            (occurrence("move-man"), occurrence("move-lady")),
        )
    )

    result = execute_document(
        dance, initial, repository=_TestRepository(), figure_executor=execute_figure
    )

    assert [node_id for node_id, _ in observed_inputs] == ["move-man", "move-lady"]
    assert observed_inputs[0][1] == observed_inputs[1][1] == initial
    assert observed_inputs[0][1] is observed_inputs[1][1]
    assert set(result.outgoing_floor.positions) == {
        (2, -1),
        (2, 1),
        (2, 2),
        (2, 4),
    }
    assert initial == floor()


def test_nested_series_and_parallel_execute_repeated_references_by_occurrence_id():
    initial = floor()
    executed = []

    def execute_figure(node, incoming, path, repository):
        executed.append((node.id, path, incoming))
        positions = dict(incoming.positions)
        if node.id == "first":
            positions[(1, -1)] = FloorEntry("M1", "male", (1, 2))
        elif node.id == "second":
            positions[(1, -1)] = FloorEntry("M1", "male", (2, 2))
        elif node.id == "third":
            positions[(2, -1)] = FloorEntry("M2", "male", (2, 2))
        return FloorState(positions)

    root = GroupNode(
        "root",
        "series",
        (
            occurrence("first", "Repeated"),
            GroupNode(
                "parallel",
                "parallel",
                (
                    occurrence("second", "Repeated"),
                    occurrence("third", "Other"),
                ),
            ),
        ),
    )

    result = execute_document(
        document(root),
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )

    assert [entry[0] for entry in executed] == ["first", "second", "third"]
    assert len({entry[0] for entry in executed}) == 3
    assert executed[0][2] == initial
    assert executed[1][2] == executed[2][2]
    assert executed[1][2].positions[(1, -1)].facing == (1, 2)
    assert executed[1][1] == ("root", "parallel")
    assert result.outgoing_floor.positions[(1, -1)].facing == (2, 2)
    assert result.outgoing_floor.positions[(2, -1)].facing == (2, 2)
    assert initial.positions[(1, -1)].facing == (1, 1)


def test_composite_occurrence_executes_embedded_children_with_inherited_anchor():
    initial = floor()
    observed = []

    def execute_figure(node, incoming, path, repository):
        observed.append((node.id, node.anchor, path, incoming))
        return incoming

    composite = CompositeOccurrence(
        "outer-composite",
        "Composite",
        (1, 1),
        (),
        GroupNode(
            "outer-group",
            "series",
            (
                CompositeOccurrence(
                    "inner-composite",
                    "Nested",
                    (2, 0),
                    (),
                    GroupNode(
                        "inner-group",
                        "series",
                        (FigureOccurrence("nested-leaf", "Wait", (0, 1), ()),),
                    ),
                ),
            ),
        ),
    )
    dance = document(GroupNode("root", "series", (composite,)))

    result = execute_document(
        dance,
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )

    assert observed == [
        (
            "nested-leaf",
            (3, 2),
            ("root", "outer-composite", "outer-group", "inner-composite", "inner-group"),
            initial,
        )
    ]
    assert result.outgoing_floor == initial
    assert initial == floor()


def test_parallel_conflicts_on_overlapping_writes_even_when_values_match():
    initial = floor()

    def execute_figure(node, incoming, path, repository):
        positions = dict(incoming.positions)
        positions[(1, -1)] = FloorEntry("M1", "male", (1, 2))
        return FloorState(positions)

    dance = document(
        GroupNode(
            "root",
            "parallel",
            (occurrence("left"), occurrence("right")),
        )
    )

    result = execute_document(
        dance,
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )

    assert result.status == "failed"
    assert result.outgoing_floor is None
    conflict = result.diagnostics[0]
    assert conflict.positions == ((1, -1),)
    assert conflict.branch_ids == ("left", "right")
    assert initial == floor()


def test_parallel_conflict_tracks_series_writes_even_when_later_child_restores_state():
    initial = floor()

    def execute_figure(node, incoming, path, repository):
        positions = dict(incoming.positions)
        if node.id == "change":
            positions[(1, -1)] = FloorEntry("M1", "male", (1, 2))
        elif node.id == "restore":
            positions[(1, -1)] = FloorEntry("M1", "male", (1, 3))
        elif node.id == "other-branch-change":
            positions[(1, -1)] = FloorEntry("M1", "male", (2, 2))
        return FloorState(positions)

    dance = document(
        GroupNode(
            "root",
            "parallel",
            (
                GroupNode(
                    "series-branch",
                    "series",
                    (occurrence("change"), occurrence("restore")),
                ),
                GroupNode(
                    "other-branch",
                    "series",
                    (
                        occurrence("other-branch-change"),
                        occurrence("other-branch-noop"),
                    ),
                ),
            ),
        )
    )

    result = execute_document(
        dance,
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )

    assert result.status == "failed"
    conflict = result.diagnostics[0]
    assert conflict.positions == ((1, -1),)
    assert conflict.branch_ids == ("series-branch", "other-branch")


def test_outer_parallel_conflict_tracks_writes_through_nested_parallel_group():
    initial = floor()

    def execute_figure(node, incoming, path, repository):
        positions = dict(incoming.positions)
        if node.id == "change":
            positions[(1, -1)] = FloorEntry("M1", "male", (1, 2))
        elif node.id == "restore":
            positions[(1, -1)] = FloorEntry("M1", "male", (1, 3))
        elif node.id == "outer-branch-change":
            positions[(1, -1)] = FloorEntry("M1", "male", (2, 2))
        return FloorState(positions)

    nested_group = GroupNode(
        "nested-parallel",
        "parallel",
        (
            GroupNode(
                "nested-series",
                "series",
                (occurrence("change"), occurrence("restore")),
            ),
        ),
    )
    dance = document(
        GroupNode(
            "root",
            "parallel",
            (
                nested_group,
                GroupNode(
                    "outer-branch",
                    "series",
                    (
                        occurrence("outer-branch-change"),
                        occurrence("outer-branch-noop"),
                    ),
                ),
            ),
        )
    )

    result = execute_document(
        dance,
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )

    assert result.status == "failed"
    conflict = result.diagnostics[0]
    assert conflict.positions == ((1, -1),)
    assert conflict.branch_ids == ("nested-parallel", "outer-branch")


def test_disjoint_parallel_merge_is_deterministic_across_child_order():
    initial = floor()

    def execute_figure(node, incoming, path, repository):
        positions = dict(incoming.positions)
        position = (2, 2) if node.id == "left" else (2, 4)
        source = (1, -1) if node.id == "left" else (1, 1)
        positions.pop(source)
        positions[position] = incoming.positions[source]
        return FloorState(positions)

    forward = document(
        GroupNode("root", "parallel", (occurrence("left"), occurrence("right")))
    )
    reverse = document(
        GroupNode("root", "parallel", (occurrence("right"), occurrence("left")))
    )

    first = execute_document(
        forward,
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )
    second = execute_document(
        reverse,
        initial,
        repository=_TestRepository(),
        figure_executor=execute_figure,
    )

    assert first.outgoing_floor == second.outgoing_floor


def test_floor_state_rejects_mutation_and_execution_failure_has_no_partial_floor():
    initial = floor()
    with pytest.raises(TypeError):
        initial.positions[(3, 1)] = FloorEntry("M3", "male", (3, 3))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        initial.positions[(1, 1)].facing = (9, 9)

    def fail_on_second(node, incoming, path, repository):
        if node.id == "second":
            raise RuntimeError("figure failed")
        return incoming

    dance = document(
        GroupNode(
            "root",
            "parallel",
            (occurrence("first"), occurrence("second")),
        )
    )
    with pytest.raises(FigureExecutionError, match="figure failed") as raised:
        execute_document(
            dance,
            initial,
            repository=_TestRepository(),
            figure_executor=fail_on_second,
        )
    assert raised.value.code == "figure_execution_failed"
    assert raised.value.node_id == "second"
    assert isinstance(raised.value.cause, RuntimeError)
    assert initial == floor()


def test_floor_state_preserves_fractional_legacy_coordinates():
    state = FloorState({(0.5, 1.5): FloorEntry("M1", "male", (1.5, 0.5))})

    assert state.positions[(0.5, 1.5)].dancer_name == "M1"
    assert state.positions[(0.5, 1.5)].facing == (1.5, 0.5)


def test_default_legacy_figure_bridge_returns_a_complete_immutable_floor():
    from src.engine.figures.capabilities import FigureRepository

    initial = FloorState(
        {
            (1, -1): FloorEntry("M1", "male", (1, 1)),
            (1, 1): FloorEntry("W1", "female", (1, -1)),
        }
    )
    dance = document(
        GroupNode("root", "series", (FigureOccurrence("wait-1", "1cWait", (1, 0), ()),))
    )

    result = execute_document(
        dance,
        initial,
        FigureRepository(),
    )

    assert set(result.outgoing_floor.positions) == {(1, -1), (1, 1)}
    assert result.outgoing_floor.positions[(1, -1)].dancer_name == "M1"
    assert result.outgoing_floor.positions[(1, 1)].dancer_name == "W1"
    assert initial.positions[(1, -1)].facing == (1, 1)


def test_default_legacy_figure_bridge_executes_fractional_figure_positions():
    from src.engine.figures.capabilities import FigureRepository

    starts = ((0, -1), (0.5, -0.5), (1.5, 0.5), (2, 1))
    initial = FloorState(
        {
            position: FloorEntry(f"Dancer-{index}", "person", position)
            for index, position in enumerate(starts)
        }
    )
    dance = document(
        GroupNode("root", "series", (FigureOccurrence("reel", "H1DR", (0, 0), ()),))
    )

    result = execute_document(
        dance,
        initial,
        FigureRepository(),
    )

    assert set(result.outgoing_floor.positions) == set(starts)
    assert len(
        {
            entry.dancer_name
            for entry in result.outgoing_floor.positions.values()
        }
    ) == 4


def test_real_legacy_dance_surfaces_conflict_inside_embedded_composite():
    from pathlib import Path

    from src.engine.domain.legacy_adapter import LegacyDanceAdapter
    from src.engine.figures.capabilities import FigureRepository
    from src.engine.models.DanceFloor import DanceFloor

    repository = FigureRepository()
    document = LegacyDanceAdapter.from_file(
        Path("data") / "Dances" / "Marries Wedding.json",
        repository.figure_exists,
        get_definition=repository.get_legacy_definition,
    )
    initial = DanceFloor("legacy input", 3)

    result = execute_document(document, initial, repository)

    assert document.incomplete is False
    assert result.status == "failed"
    conflict = next(
        diagnostic
        for diagnostic in result.diagnostics
        if isinstance(diagnostic, ParallelWriteConflict)
    )
    conflicted_group = document.find_node(conflict.group_id)
    assert isinstance(conflicted_group, GroupNode)
    assert conflicted_group.kind == "parallel"
    assert conflict.positions
    assert len(initial.DanceFloorMap) == 6
