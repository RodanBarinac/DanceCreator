"""Preflight duration calculation for canonical dance trees."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.engine.figures.addon_utils import duration_addon_bars

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceNode,
    FigureOccurrence,
    GroupNode,
)


class ExecutionError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        node_id: str | None = None,
        path: tuple[str, ...] = (),
    ) -> None:
        self.code = code
        self.node_id = node_id
        self.path = path
        super().__init__(message)


class ParallelDurationError(ExecutionError):
    """A parallel group has child paths with different durations."""

    def __init__(
        self,
        *,
        group_id: str,
        path: tuple[str, ...],
        path_durations: Mapping[str, int],
    ) -> None:
        self.code = "parallel_duration_mismatch"
        self.group_id = group_id
        self.path = path
        self.path_durations = dict(path_durations)
        details = ", ".join(
            f"{child_id}={duration}"
            for child_id, duration in self.path_durations.items()
        )
        super().__init__(
            code=self.code,
            message=(
                f"Parallel group {group_id!r} at {'.'.join(path)} has unequal "
                f"path durations: {details}"
            ),
            node_id=group_id,
            path=path,
        )


class DurationUnavailableError(ExecutionError):
    """A figure duration cannot be established from the repository."""

    def __init__(
        self,
        *,
        occurrence_id: str,
        figure_ref: str,
        path: tuple[str, ...],
    ) -> None:
        self.figure_ref = figure_ref
        super().__init__(
            code="duration_unavailable",
            message=(
                f"Cannot determine duration for figure occurrence "
                f"{occurrence_id!r} ({figure_ref!r})."
            ),
            node_id=occurrence_id,
            path=path,
        )


@dataclass(frozen=True)
class DurationAnalysis:
    """Calculated duration for each node and the root duration."""

    node_durations: Mapping[str, int | None]
    duration: int | None


def analyze_durations(node: DanceNode, repository: object) -> DurationAnalysis:
    """Calculate recursive durations and reject every known unequal parallel."""
    durations: dict[str, int | None] = {}
    _duration(node, repository, (), durations)
    return DurationAnalysis(durations, durations[node.id])


def _duration(
    node: DanceNode,
    repository: object,
    path: tuple[str, ...],
    durations: dict[str, int | None],
) -> int | None:
    if isinstance(node, FigureOccurrence):
        if repository is None:
            raise DurationUnavailableError(
                occurrence_id=node.id,
                figure_ref=node.figure_ref,
                path=path,
            )
        getter = getattr(repository, "get_definition", None)
        if not callable(getter):
            raise TypeError("Figure repository must provide get_definition()")
        definition = getter(node.figure_ref)
        bars = getattr(definition, "bars", None)
        if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1:
            raise ValueError(
                f"Figure {node.figure_ref!r} Bars must be a positive integer"
            )
        addon_definitions = {
            addon.get("name"): addon.get("parameters", {})
            for addon in getattr(definition, "valid_addons", ())
            if isinstance(addon, dict)
        }
        duration_addons = [name for name in node.addons if duration_addon_bars(name) is not None]
        if len(duration_addons) > 1:
            raise ValueError(
                f"Conflicting duration addons {duration_addons[0]!r} and "
                f"{duration_addons[1]!r} both modify Bars."
            )
        for addon_name in node.addons:
            dynamic_bars = duration_addon_bars(addon_name)
            if dynamic_bars is not None:
                bars = dynamic_bars
                continue
            addon = addon_definitions.get(addon_name, {})
            if "Bars" in addon:
                addon_bars = addon["Bars"]
                if (
                    isinstance(addon_bars, bool)
                    or not isinstance(addon_bars, int)
                    or addon_bars < 1
                ):
                    raise ValueError(
                        f"Addon {addon_name!r} Bars must be a positive integer"
                    )
                bars = addon_bars
        result = bars
        durations[node.id] = result
        return result

    if isinstance(node, CompositeOccurrence):
        result = _duration(node.root, repository, path + (node.id,), durations)
        durations[node.id] = result
        return result

    if not isinstance(node, GroupNode):
        raise TypeError(f"Unsupported dance node: {type(node).__name__}")

    group_path = path + (node.id,)
    child_durations = tuple(
        (child, _duration(child, repository, group_path, durations))
        for child in node.children
    )
    values = tuple(duration for _, duration in child_durations)
    if node.kind == "series":
        result = None if any(value is None for value in values) else sum(values)
    elif values and all(value is not None for value in values):
        path_durations = {
            child.id: duration for child, duration in child_durations
        }
        if len(set(path_durations.values())) != 1:
            raise ParallelDurationError(
                group_id=node.id,
                path=group_path,
                path_durations=path_durations,
            )
        result = values[0]
    elif not values:
        result = 0
    else:
        result = None

    durations[node.id] = result
    return result
