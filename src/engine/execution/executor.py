"""Execution of canonical dance trees with isolated deterministic branches."""

from __future__ import annotations

from dataclasses import dataclass, replace
from numbers import Real
from typing import Callable, Iterable, Mapping

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    FigureOccurrence,
    GroupNode,
)
from src.engine.execution.combine import (
    BranchResult,
    FloorEntry,
    FloorState,
    Position,
    ParallelWriteConflict,
    changed_positions,
    combine_parallel,
)
from src.engine.execution.duration import ExecutionError, analyze_durations
from src.engine.execution.trace import BranchSummary, TraceRecord


class FigureExecutionError(ExecutionError):
    def __init__(
        self,
        *,
        occurrence: FigureOccurrence,
        path: tuple[str, ...],
        cause: Exception,
    ) -> None:
        self.figure_ref = occurrence.figure_ref
        self.occurrence = occurrence
        self.cause = cause
        self.code = getattr(cause, "code", "figure_execution_failed")
        super().__init__(
            code=self.code,
            message=(
                f"Figure occurrence {occurrence.id!r} ({occurrence.figure_ref!r}) "
                f"failed: {cause}"
            ),
            node_id=occurrence.id,
            path=path,
        )


@dataclass(frozen=True)
class NodeExecution:
    node_id: str
    incoming_floor: FloorState
    outgoing_floor: FloorState | None
    duration: int | None
    trace_records: tuple[TraceRecord, ...]
    writes: frozenset[Position]
    diagnostics: tuple[object, ...] = ()
    status: str = "completed"
    last_valid_floor: FloorState | None = None


@dataclass(frozen=True)
class ExecutionResult:
    outgoing_floor: FloorState | None
    duration: int | None
    trace_records: tuple[TraceRecord, ...]
    diagnostics: tuple[object, ...]
    status: str = "completed"
    last_valid_floor: FloorState | None = None


FigureExecutor = Callable[
    [FigureOccurrence, FloorState, tuple[str, ...], object],
    FloorState,
]


@dataclass(frozen=True)
class _ExecutionContext:
    repository: object
    figure_executor: FigureExecutor | None
    durations: Mapping[str, int | None]
    anchor_offset: tuple[Real, Real] = (0, 0)


def _active_union(results: Iterable[NodeExecution]) -> frozenset[str] | None:
    active = set()
    for result in results:
        dancers = result.trace_records[0].active_dancers
        if dancers is None:
            return None
        active.update(dancers)
    return frozenset(active)


def _active_identities(incoming: FloorState, starts: set[Position]) -> frozenset[str] | None:
    """Names must uniquely identify dancers before they can safely filter snapshots."""
    names = [entry.dancer_name for entry in incoming.positions.values()]
    if any(not name for name in names) or len(names) != len(set(names)):
        return None
    return frozenset(incoming.positions[position].dancer_name for position in starts)


def execute_document(
    document: DanceDocument,
    initial_floor: FloorState | object,
    repository: object,
    *,
    figure_executor: FigureExecutor | None = None,
    bar_start: int = 1,
) -> ExecutionResult:
    if document.incomplete:
        raise ExecutionError(
            code="incomplete_document",
            message="Cannot execute an incomplete dance document.",
            node_id=document.root.id,
        )
    duration_analysis = analyze_durations(document.root, repository)
    incoming = (
        initial_floor
        if isinstance(initial_floor, FloorState)
        else FloorState.from_legacy(initial_floor)
    )
    result = execute_node(
        document.root,
        incoming,
        (),
        _ExecutionContext(
            repository,
            figure_executor,
            duration_analysis.node_durations,
        ),
        bar_start,
    )
    return ExecutionResult(
        outgoing_floor=result.outgoing_floor,
        duration=result.duration,
        trace_records=result.trace_records,
        diagnostics=result.diagnostics,
        status=result.status,
        last_valid_floor=(
            result.last_valid_floor
            if result.last_valid_floor is not None
            else incoming
        ),
    )


def execute_node(
    node: DanceNode,
    incoming: FloorState,
    path: tuple[str, ...],
    context: _ExecutionContext,
    bar_start: int = 1,
) -> NodeExecution:
    duration = context.durations[node.id]
    bar_range = _bar_range(bar_start, duration)
    if isinstance(node, CompositeOccurrence):
        composite_context = replace(
            context,
            anchor_offset=(
                context.anchor_offset[0] + node.anchor[0],
                context.anchor_offset[1] + node.anchor[1],
            ),
        )
        result = execute_node(
            node.root,
            incoming,
            path + (node.id,),
            composite_context,
            bar_start,
        )
        trace = TraceRecord(
            node_id=node.id,
            kind="composite",
            node_path=path + (node.id,),
            group_path=path,
            parent_group=path[-1] if path else None,
            figure_ref=node.figure_ref,
            bar_range=bar_range,
            incoming_floor=incoming,
            outgoing_floor=result.outgoing_floor,
            status=result.status,
            writes=result.writes,
            duration=duration,
            active_dancers=result.trace_records[0].active_dancers,
        )
        return NodeExecution(
            node_id=node.id,
            incoming_floor=incoming,
            outgoing_floor=result.outgoing_floor,
            duration=result.duration,
            trace_records=(trace,) + result.trace_records,
            writes=result.writes,
            diagnostics=result.diagnostics,
            status=result.status,
            last_valid_floor=result.last_valid_floor,
        )
    if isinstance(node, FigureOccurrence):
        effective_occurrence = replace(
            node,
            anchor=(
                node.anchor[0] + context.anchor_offset[0],
                node.anchor[1] + context.anchor_offset[1],
            ),
        )
        return _execute_occurrence(
            effective_occurrence, incoming, path, context, bar_start
        )
    if not isinstance(node, GroupNode):
        raise TypeError(f"Unsupported dance node: {type(node).__name__}")

    child_path = path + (node.id,)
    if node.kind == "series":
        current = incoming
        cursor = bar_start
        child_results = []
        for child in node.children:
            result = execute_node(child, current, child_path, context, cursor)
            child_results.append(result)
            child_duration = context.durations[child.id]
            if child_duration is not None:
                cursor += child_duration
            if result.status == "failed":
                break
            current = result.outgoing_floor
        failed = any(result.status == "failed" for result in child_results)
        outgoing = None if failed else current
        last_valid = outgoing
        if failed:
            last_valid = child_results[-1].last_valid_floor
            if last_valid is None:
                last_valid = current
        writes = frozenset().union(*(result.writes for result in child_results))
        trace = TraceRecord(
            node_id=node.id,
            kind="series",
            node_path=child_path,
            group_path=path,
            parent_group=path[-1] if path else None,
            figure_ref=None,
            bar_range=bar_range,
            incoming_floor=incoming,
            outgoing_floor=outgoing,
            status="failed" if failed else "completed",
            writes=writes,
            duration=duration,
            active_dancers=(
                _active_union(child_results)
                if len(child_results) == len(node.children) else None
            ),
        )
        return NodeExecution(
            node_id=node.id,
            incoming_floor=incoming,
            outgoing_floor=outgoing,
            trace_records=(trace,)
            + tuple(
                record
                for result in child_results
                for record in result.trace_records
            ),
            writes=writes,
            duration=duration,
            diagnostics=tuple(
                diagnostic
                for result in child_results
                for diagnostic in result.diagnostics
            ),
            status="failed" if failed else "completed",
            last_valid_floor=last_valid,
        )

    branches = tuple(
        execute_node(child, incoming, child_path, context, bar_start)
        for child in node.children
    )
    conflict = None
    diagnostics = tuple(
        diagnostic
        for result in branches
        for diagnostic in result.diagnostics
    )
    merged = None
    if all(result.status == "completed" for result in branches):
        try:
            merged = combine_parallel(
                incoming,
                node.id,
                tuple(
                    BranchResult(result.node_id, result.outgoing_floor, result.writes)
                    for result in branches
                ),
            )
        except ParallelWriteConflict as error:
            conflict = error
            diagnostics += (error,)
    failed = merged is None
    writes = frozenset().union(*(result.writes for result in branches))
    summaries = tuple(
        BranchSummary(
            node_id=result.node_id,
            status=result.status,
            outgoing_floor=result.outgoing_floor,
            writes=result.writes,
        )
        for result in branches
    )
    trace = TraceRecord(
        node_id=node.id,
        kind="parallel",
        node_path=child_path,
        group_path=path,
        parent_group=path[-1] if path else None,
        figure_ref=None,
        bar_range=bar_range,
        incoming_floor=incoming,
        outgoing_floor=merged,
        status="failed" if failed else "completed",
        writes=writes,
        branch_summaries=summaries,
        conflict=conflict,
        duration=duration,
        active_dancers=_active_union(branches),
    )
    return NodeExecution(
        node_id=node.id,
        incoming_floor=incoming,
        outgoing_floor=merged,
        trace_records=(trace,)
        + tuple(
            record
            for result in branches
            for record in result.trace_records
        ),
        writes=writes,
        duration=duration,
        diagnostics=diagnostics,
        status="failed" if failed else "completed",
        last_valid_floor=incoming if failed else merged,
    )


def _execute_occurrence(
    occurrence: FigureOccurrence,
    incoming: FloorState,
    path: tuple[str, ...],
    context: _ExecutionContext,
    bar_start: int,
) -> NodeExecution:
    try:
        if context.figure_executor is not None:
            outgoing = context.figure_executor(
                occurrence, incoming, path, context.repository
            )
            active_dancers = None
            if not isinstance(outgoing, FloorState):
                raise TypeError("Figure executor must return a FloorState")
        else:
            outgoing, active_dancers = _execute_legacy_figure(
                occurrence, incoming, path, context.repository
            )
    except ExecutionError:
        raise
    except Exception as error:
        raise FigureExecutionError(
            occurrence=occurrence, path=path, cause=error
        ) from error
    writes = changed_positions(incoming, outgoing)
    return NodeExecution(
        node_id=occurrence.id,
        incoming_floor=incoming,
        outgoing_floor=outgoing,
        duration=context.durations[occurrence.id],
        trace_records=(
            TraceRecord(
                node_id=occurrence.id,
                kind="figure",
                node_path=path + (occurrence.id,),
                group_path=path,
                parent_group=path[-1] if path else None,
                figure_ref=occurrence.figure_ref,
                bar_range=_bar_range(bar_start, context.durations[occurrence.id]),
                incoming_floor=incoming,
                outgoing_floor=outgoing,
                status="completed",
                writes=writes,
                duration=context.durations[occurrence.id],
                active_dancers=active_dancers,
            ),
        ),
        writes=writes,
        last_valid_floor=outgoing,
    )


def _bar_range(start: int, duration: int | None) -> tuple[int, int] | None:
    if duration is None or duration == 0:
        return None
    return (start, start + duration - 1)


def _execute_legacy_figure(
    occurrence: FigureOccurrence,
    incoming: FloorState,
    path: tuple[str, ...],
    repository: object,
) -> tuple[FloorState, frozenset[str] | None]:
    from src.engine.figures.SimpleFigure import SimpleFigure

    if repository is not None and hasattr(repository, "validate_addons"):
        repository.validate_addons(
            occurrence.figure_ref,
            occurrence.addons,
            path=".".join(path + (occurrence.id,)),
            occurrence_id=occurrence.id,
        )

    figure = SimpleFigure(
        occurrence.figure_ref,
        list(occurrence.anchor),
        list(occurrence.addons),
    )
    missing_starts = [
        tuple(figure.posWithAnchor(start))
        for start in figure.StartPos
        if tuple(figure.posWithAnchor(start)) not in incoming.positions
    ]
    if missing_starts:
        raise ValueError(
            f"Missing dancer at figure StartPos {missing_starts[0]!r}; "
            "figure execution requires a dancer at every declared start position."
        )
    legacy_outgoing = figure.DanceMove(incoming.to_legacy())

    # Legacy atomic figures return only moved dancers. Reconstruct a complete
    # floor before deriving the node's changed-position write set.
    positions = dict(incoming.positions)
    starts = {
        figure.posWithAnchor(start)
        for start in figure.StartPos
    }
    for position in starts:
        positions.pop(tuple(position), None)
    for position, (dancer, facing) in legacy_outgoing.DanceFloorMap.items():
        positions[tuple(position)] = FloorEntry(
            str(dancer.name),
            str(getattr(dancer, "gender", "")),
            facing,
        )
    return FloorState(positions), _active_identities(incoming, starts)
