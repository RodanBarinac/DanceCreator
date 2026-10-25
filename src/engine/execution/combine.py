"""Immutable floor values and deterministic parallel branch merging."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping, Tuple


Position = Tuple[Real, Real]


def _freeze(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    return value


@dataclass(frozen=True)
class FloorEntry:
    """The semantic dancer and facing stored at a floor position."""

    dancer_name: str
    dancer_gender: str
    facing: Any

    def __post_init__(self) -> None:
        if not isinstance(self.dancer_name, str):
            raise TypeError("Dancer name must be a string")
        if not isinstance(self.dancer_gender, str):
            raise TypeError("Dancer gender must be a string")
        object.__setattr__(self, "facing", _freeze(self.facing))


@dataclass(frozen=True, init=False)
class FloorState:
    """A snapshot of occupied floor positions with no mutable legacy objects."""

    positions: Mapping[Position, FloorEntry]

    def __init__(self, positions: Mapping[Position, FloorEntry]) -> None:
        if not isinstance(positions, Mapping):
            raise TypeError("Floor positions must be a mapping")
        copied: dict[Position, FloorEntry] = {}
        for position, entry in positions.items():
            if (
                not isinstance(position, tuple)
                or len(position) != 2
                or any(
                    isinstance(value, bool) or not isinstance(value, Real)
                    for value in position
                )
            ):
                raise ValueError("Floor positions must be pairs of real numbers")
            if not isinstance(entry, FloorEntry):
                raise TypeError("Floor positions must contain FloorEntry values")
            copied[position] = entry
        object.__setattr__(self, "positions", MappingProxyType(copied))

    @classmethod
    def from_legacy(cls, dance_floor: Any) -> FloorState:
        """Snapshot an existing DanceFloor without retaining its mutable dancers."""
        positions = {}
        for position, (dancer, facing) in dance_floor.DanceFloorMap.items():
            positions[tuple(position)] = FloorEntry(
                str(dancer.name),
                str(getattr(dancer, "gender", "")),
                facing,
            )
        return cls(positions)

    def to_legacy(self):
        """Build a private legacy floor for one figure execution."""
        from src.engine.models.DanceFloor import DanceFloor
        from src.engine.models.Dancer import Dancer

        floor = DanceFloor("execution-input")
        for position, entry in sorted(self.positions.items()):
            floor.addDancer(
                Dancer(entry.dancer_name, entry.dancer_gender),
                position,
                _thaw(entry.facing),
            )
        return floor


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    return value


def changed_positions(before: FloorState, after: FloorState) -> frozenset[Position]:
    """Return positions whose complete semantic contents differ."""
    return frozenset(
        position
        for position in before.positions.keys() | after.positions.keys()
        if before.positions.get(position) != after.positions.get(position)
    )


@dataclass(frozen=True)
class BranchResult:
    node_id: str
    outgoing_floor: FloorState
    writes: frozenset[Position]


class ParallelWriteConflict(RuntimeError):
    """Raised when two parallel branches change the same floor position."""

    def __init__(
        self,
        *,
        group_id: str,
        conflicts: Mapping[Position, tuple[str, ...]],
    ) -> None:
        self.code = "parallel_write_conflict"
        self.group_id = group_id
        self.conflicts = MappingProxyType(dict(sorted(conflicts.items())))
        self.positions = tuple(self.conflicts)
        self.branch_ids = tuple(
            dict.fromkeys(
                branch_id
                for branch_ids in self.conflicts.values()
                for branch_id in branch_ids
            )
        )
        details = ", ".join(
            f"{position}: {', '.join(branch_ids)}"
            for position, branch_ids in self.conflicts.items()
        )
        super().__init__(f"Parallel group {group_id!r} has overlapping writes: {details}")


def combine_parallel(
    incoming: FloorState,
    group_id: str,
    branches: tuple[BranchResult, ...],
) -> FloorState:
    """Overlay disjoint branch deltas, rejecting every overlapping write."""
    writers: dict[Position, list[str]] = {}
    for branch in branches:
        for position in branch.writes:
            writers.setdefault(position, []).append(branch.node_id)
    conflicts = {
        position: tuple(branch_ids)
        for position, branch_ids in writers.items()
        if len(branch_ids) > 1
    }
    if conflicts:
        raise ParallelWriteConflict(group_id=group_id, conflicts=conflicts)

    merged = dict(incoming.positions)
    for branch in branches:
        for position in sorted(branch.writes):
            if position in branch.outgoing_floor.positions:
                merged[position] = branch.outgoing_floor.positions[position]
            else:
                merged.pop(position, None)
    return FloorState(merged)
