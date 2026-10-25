"""Immutable execution trace read models."""

from __future__ import annotations

from dataclasses import dataclass

from src.engine.execution.combine import FloorState, ParallelWriteConflict, Position


@dataclass(frozen=True)
class BranchSummary:
    """Outcome of one isolated child of a parallel group."""

    node_id: str
    status: str
    outgoing_floor: FloorState | None
    writes: frozenset[Position]


@dataclass(frozen=True)
class TraceRecord:
    """One occurrence or structural node's immutable execution snapshot."""

    node_id: str
    kind: str
    node_path: tuple[str, ...]
    group_path: tuple[str, ...]
    parent_group: str | None
    figure_ref: str | None
    bar_range: tuple[int, int] | None
    incoming_floor: FloorState
    outgoing_floor: FloorState | None
    status: str
    writes: frozenset[Position]
    branch_summaries: tuple[BranchSummary, ...] = ()
    conflict: ParallelWriteConflict | None = None
    duration: int | None = None
