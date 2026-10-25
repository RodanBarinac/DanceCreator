from types import SimpleNamespace

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.execution.executor import execute_document


def _figure(node_id, figure_ref="Move"):
    return FigureOccurrence(node_id, figure_ref, (0, 0), ())


def _document(root):
    return DanceDocument(1, {}, root)


class _Repository:
    def get_definition(self, figure_ref):
        return SimpleNamespace(bars=2)


def _replace_facing(incoming, position, facing):
    positions = dict(incoming.positions)
    entry = positions[position]
    positions[position] = FloorEntry(
        entry.dancer_name, entry.dancer_gender, facing
    )
    return FloorState(positions)


def _trace_by_id(result):
    return {record.node_id: record for record in result.trace_records}


def test_trace_paths_and_ranges_follow_series_parallel_and_composite_structure():
    root = GroupNode(
        "root",
        "series",
        (
            _figure("first"),
            GroupNode(
                "parallel",
                "parallel",
                (
                    _figure("left"),
                    CompositeOccurrence(
                        "composite",
                        "Compound",
                        (1, 2),
                        (),
                        GroupNode("embedded", "series", (_figure("inside"),)),
                    ),
                ),
            ),
        ),
    )
    result = execute_document(
        _document(root), FloorState({}), _Repository(), figure_executor=lambda n, f, p, r: f
    )

    records = _trace_by_id(result)
    assert records["root"].node_path == ("root",)
    assert records["parallel"].node_path == ("root", "parallel")
    assert records["left"].node_path == ("root", "parallel", "left")
    assert records["composite"].group_path == ("root", "parallel")
    assert records["inside"].node_path == (
        "root", "parallel", "composite", "embedded", "inside"
    )
    assert records["first"].bar_range == (1, 2)
    assert records["left"].bar_range == records["inside"].bar_range == (3, 4)
    assert records["parallel"].bar_range == (3, 4)
    assert records["composite"].figure_ref == "Compound"


def test_occurrence_snapshots_are_independent_and_parallel_children_are_isolated():
    initial = FloorState({(1, 1): FloorEntry("D", "person", (1, 1))})
    root = GroupNode(
        "root",
        "series",
        (
            _figure("first", "Repeated"),
            GroupNode(
                "parallel",
                "parallel",
                (_figure("left", "Repeated"), _figure("right", "Repeated")),
            ),
        ),
    )

    def execute(node, incoming, path, repository):
        if node.id == "first":
            return _replace_facing(incoming, (1, 1), (1, 2))
        position = (2, 1) if node.id == "left" else (3, 1)
        positions = dict(incoming.positions)
        positions[position] = FloorEntry(node.id, "person", (1, 1))
        return FloorState(positions)

    result = execute_document(_document(root), initial, _Repository(), figure_executor=execute)
    records = _trace_by_id(result)
    assert records["first"].outgoing_floor is records["left"].incoming_floor
    assert records["left"].incoming_floor is records["right"].incoming_floor
    assert records["left"].outgoing_floor.positions[(2, 1)].facing == (1, 1)
    assert records["right"].outgoing_floor.positions[(3, 1)].facing == (1, 1)
    assert records["left"].outgoing_floor is not records["right"].outgoing_floor
    assert records["parallel"].outgoing_floor == result.outgoing_floor


def test_success_trace_has_inclusive_ranges_and_only_occurrence_snapshots():
    root = GroupNode("root", "series", (_figure("one"), _figure("two")))
    result = execute_document(
        _document(root), FloorState({}), _Repository(), figure_executor=lambda n, f, p, r: f
    )

    records = _trace_by_id(result)
    assert result.status == "completed"
    assert records["root"].status == "completed"
    assert records["one"].bar_range == (1, 2)
    assert records["two"].bar_range == (3, 4)
    assert records["one"].outgoing_floor is records["two"].incoming_floor
    assert not hasattr(records["one"], "bar_snapshots")


def test_parallel_conflict_returns_failed_result_with_isolated_traces():
    initial = FloorState({(1, 1): FloorEntry("D", "person", (1, 1))})
    root = GroupNode("root", "series", (_figure("prefix"), GroupNode(
        "parallel", "parallel", (_figure("left"), _figure("right"))
    )))

    def execute(node, incoming, path, repository):
        facing = (2, 1) if node.id == "left" else (3, 1)
        if node.id == "prefix":
            facing = (1, 2)
        return _replace_facing(incoming, (1, 1), facing)

    result = execute_document(_document(root), initial, _Repository(), figure_executor=execute)
    records = _trace_by_id(result)

    assert result.status == "failed"
    assert result.outgoing_floor is None
    assert result.last_valid_floor == records["prefix"].outgoing_floor
    assert records["parallel"].outgoing_floor is None
    assert records["root"].outgoing_floor is None
    assert records["left"].outgoing_floor.positions[(1, 1)].facing == (2, 1)
    assert records["right"].outgoing_floor.positions[(1, 1)].facing == (3, 1)
    conflict = result.diagnostics[0]
    assert conflict.code == "parallel_write_conflict"
    assert conflict.conflicts == {(1, 1): ("left", "right")}
    parallel = records["parallel"]
    assert parallel.conflict is conflict
    assert [
        (branch.node_id, branch.status, branch.outgoing_floor)
        for branch in parallel.branch_summaries
    ] == [
        ("left", "completed", records["left"].outgoing_floor),
        ("right", "completed", records["right"].outgoing_floor),
    ]
    assert initial.positions[(1, 1)].facing == (1, 1)


def test_nested_parallel_conflict_propagates_but_siblings_execute_and_series_stops():
    initial = FloorState({(1, 1): FloorEntry("D", "person", (1, 1))})
    calls = []
    root = GroupNode(
        "root",
        "series",
        (
            _figure("prefix"),
            GroupNode(
                "outer-parallel",
                "parallel",
                (
                    CompositeOccurrence(
                        "wrapped-conflict",
                        "Wrapped",
                        (0, 0),
                        (),
                        GroupNode(
                            "composite-root",
                            "series",
                            (
                                GroupNode(
                                    "nested", "parallel", (_figure("a"), _figure("b"))
                                ),
                            ),
                        ),
                    ),
                    _figure("sibling"),
                ),
            ),
            _figure("after-failure"),
        ),
    )

    def execute(node, incoming, path, repository):
        calls.append(node.id)
        if node.id in ("a", "b"):
            return _replace_facing(incoming, (1, 1), (2 if node.id == "a" else 3, 1))
        return incoming

    result = execute_document(_document(root), initial, _Repository(), figure_executor=execute)
    records = _trace_by_id(result)
    assert calls == ["prefix", "a", "b", "sibling"]
    assert result.status == "failed"
    assert result.last_valid_floor is records["prefix"].outgoing_floor
    assert records["nested"].outgoing_floor is None
    assert records["wrapped-conflict"].status == "failed"
    assert records["wrapped-conflict"].outgoing_floor is None
    assert records["outer-parallel"].outgoing_floor is None
    assert records["root"].outgoing_floor is None
    assert "after-failure" not in records
    assert any(item.code == "parallel_write_conflict" for item in result.diagnostics)


def test_last_valid_floor_tracks_valid_prefix_inside_failed_composite():
    initial = FloorState({(1, 1): FloorEntry("D", "person", (1, 1))})
    root = GroupNode(
        "root",
        "series",
        (
            _figure("top-prefix"),
            CompositeOccurrence(
                "composite",
                "Compound",
                (0, 0),
                (),
                GroupNode(
                    "composite-root",
                    "series",
                    (
                        _figure("local-prefix"),
                        GroupNode("parallel", "parallel", (_figure("a"), _figure("b"))),
                    ),
                ),
            ),
        ),
    )

    def execute(node, incoming, path, repository):
        facing = {
            "top-prefix": (1, 2),
            "local-prefix": (1, 3),
            "a": (2, 1),
            "b": (3, 1),
        }.get(node.id)
        return incoming if facing is None else _replace_facing(incoming, (1, 1), facing)

    result = execute_document(_document(root), initial, _Repository(), figure_executor=execute)
    records = _trace_by_id(result)

    assert result.status == "failed"
    assert result.outgoing_floor is None
    assert result.last_valid_floor is records["local-prefix"].outgoing_floor
    assert records["composite"].outgoing_floor is None


def test_execution_result_and_nodes_retain_preflight_durations():
    root = GroupNode("root", "series", (_figure("one"), _figure("two")))
    result = execute_document(
        _document(root), FloorState({}), _Repository(), figure_executor=lambda n, f, p, r: f
    )

    assert result.duration == 4
    assert _trace_by_id(result)["one"].duration == 2
