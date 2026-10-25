"""Ordered validation of canonical dance documents."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    FigureOccurrence,
    GroupNode,
)
from src.engine.execution.combine import FloorState
from src.engine.execution.duration import (
    DurationUnavailableError,
    ExecutionError,
    ParallelDurationError,
    analyze_durations,
)
from src.engine.execution.executor import (
    FigureExecutionError,
    execute_document,
)
from src.engine.execution.trace import TraceRecord
from src.engine.figures.capabilities import AddonValidationError
from src.engine.validation.errors import ValidationIssue, ValidationReport


@dataclass(frozen=True)
class _NodeLocation:
    node: DanceNode
    path: str
    order: int


def validate_document(
    document: object,
    initial_floor: object,
    repository: object,
) -> ValidationReport:
    """Validate structure, references/capabilities, durations, then execution."""
    locations, structure_errors = _index_and_check_structure(document)
    if structure_errors:
        return ValidationReport(errors=tuple(structure_errors))

    assert isinstance(document, DanceDocument)
    try:
        floor = (
            initial_floor
            if isinstance(initial_floor, FloorState)
            else FloorState.from_legacy(initial_floor)
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        return ValidationReport(
            errors=(
                _issue(
                    "invalid_document_structure",
                    "initialFloor",
                    "initialFloor",
                    f"Initial floor is not a valid floor snapshot: {error}",
                ),
            )
        )

    reference_errors = _validate_references_and_capabilities(
        document, locations, repository
    )
    addon_error_codes = {
        "unsupported_addon",
        "invalid_addon_selection",
        "invalid_addon_combination",
    }
    blocked_occurrences = {
        issue.occurrence_id
        for issue in reference_errors
        if issue.occurrence_id is not None and issue.code not in addon_error_codes
    }
    duration_errors = (
        _duration_issues(document.root, locations, repository, blocked_occurrences)
        if repository is not None
        else []
    )
    errors = reference_errors + duration_errors
    if errors:
        return ValidationReport(errors=tuple(errors))

    try:
        result = execute_document(document, floor, repository)
    except FigureExecutionError as error:
        return ValidationReport(
            errors=(
                _issue(
                    error.code,
                    _path_for_id(locations, error.node_id),
                    "execution",
                    str(error),
                    node_id=error.node_id,
                    occurrence_id=error.node_id,
                    details={
                        "figureRef": error.figure_ref,
                        "dancers": _affected_occurrence_dancers(
                            error.occurrence, floor
                        ),
                    },
                ),
            )
        )

    conflicts = _conflict_issues(locations, result.trace_records)
    if result.status != "completed" and not conflicts:
        return ValidationReport(
            errors=(
                _issue(
                    "execution_failed",
                    "root",
                    "execution",
                    "Document execution failed without a structured conflict trace.",
                    node_id=document.root.id,
                    details={"status": result.status},
                ),
            )
        )
    return ValidationReport(errors=tuple(conflicts))


def _duration_issues(
    root: GroupNode,
    locations: dict[str, _NodeLocation],
    repository: object,
    blocked_occurrences: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[tuple[str, str | None]] = set()

    def add(issue: ValidationIssue) -> None:
        key = (issue.code, issue.node_id)
        if key not in seen:
            seen.add(key)
            issues.append(issue)

    for location in sorted(
        locations.values(), key=lambda item: item.order, reverse=True
    ):
        node = location.node
        if isinstance(node, FigureOccurrence):
            if node.id in blocked_occurrences:
                continue
            try:
                analyze_durations(node, repository)
            except (FileNotFoundError, KeyError):
                add(_missing_reference(node, location.path))
            except DurationUnavailableError as error:
                add(
                    _issue(
                        error.code,
                        location.path,
                        "duration",
                        str(error),
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={"figureRef": error.figure_ref},
                    )
                )
            except ValueError as error:
                add(
                    _issue(
                        "invalid_figure_duration",
                        location.path,
                        "duration",
                        str(error),
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={"figureRef": node.figure_ref},
                    )
                )
            continue
        if not isinstance(node, GroupNode) or node.kind != "parallel":
            continue
        try:
            analyze_durations(node, repository)
        except ParallelDurationError as error:
            if error.group_id == node.id:
                add(
                    _issue(
                        error.code,
                        location.path,
                        "duration",
                        str(error),
                        node_id=node.id,
                        details={
                            "groupId": node.id,
                            "pathDurations": dict(error.path_durations),
                        },
                    )
                )
        except DurationUnavailableError as error:
            if error.node_id not in blocked_occurrences:
                add(
                    _issue(
                        error.code,
                        _path_for_id(locations, error.node_id),
                        "duration",
                        str(error),
                        node_id=error.node_id,
                        occurrence_id=error.node_id,
                        details={"figureRef": error.figure_ref},
                    )
                )
        except ExecutionError as error:
            if error.node_id not in blocked_occurrences:
                add(
                    _issue(
                        error.code,
                        _path_for_id(locations, error.node_id),
                        "duration",
                        str(error),
                        node_id=error.node_id,
                        details={"executionCode": error.code},
                    )
                )
        except (FileNotFoundError, KeyError, ValueError):
            # The leaf pass reports unavailable or invalid Bars at occurrence paths.
            continue

    return sorted(
        issues,
        key=lambda issue: locations[issue.node_id].order
        if issue.node_id in locations
        else len(locations),
    )


def _index_and_check_structure(
    document: object,
) -> tuple[dict[str, _NodeLocation], list[ValidationIssue]]:
    if not isinstance(document, DanceDocument):
        return {}, [
            _issue(
                "invalid_document_structure",
                "document",
                "structure",
                "Expected a canonical DanceDocument.",
            )
        ]

    issues: list[ValidationIssue] = []
    unresolved_are_valid = (
        isinstance(document.unresolved_references, tuple)
        and all(
            isinstance(reference, str) and bool(reference)
            for reference in document.unresolved_references
        )
        and len(set(document.unresolved_references))
        == len(document.unresolved_references)
    )
    if (
        isinstance(document.format_version, bool)
        or document.format_version != 1
        or not isinstance(document.metadata, dict)
        or not isinstance(document.incomplete, bool)
        or not unresolved_are_valid
        or document.incomplete != bool(document.unresolved_references)
        or isinstance(document.revision, bool)
        or not isinstance(document.revision, int)
        or document.revision < 0
    ):
        issues.append(
            _issue(
                "invalid_document_structure",
                "document",
                "structure",
                "Dance document metadata, status, or format version is invalid.",
            )
        )
    if not isinstance(document.root, GroupNode):
        issues.append(
            _issue(
                "invalid_document_structure",
                "root",
                "structure",
                "Dance document root must be a group.",
            )
        )
        return {}, issues

    locations: dict[str, _NodeLocation] = {}
    occurrence_refs: set[str] = set()
    order = 0

    def walk(node: object, path: str) -> None:
        nonlocal order
        if not isinstance(node, (GroupNode, FigureOccurrence, CompositeOccurrence)):
            issues.append(
                _issue(
                    "invalid_document_structure",
                    path,
                    "structure",
                    "Dance tree contains an unsupported node.",
                )
            )
            return
        node_id = getattr(node, "id", None)
        if not isinstance(node_id, str) or not node_id:
            issues.append(
                _issue(
                    "invalid_document_structure",
                    path,
                    "structure",
                    "Dance tree node must have a non-empty ID.",
                )
            )
            return
        if node_id in locations:
            issues.append(
                _issue(
                    "invalid_document_structure",
                    path,
                    "structure",
                    f"Duplicate dance node ID {node_id!r}.",
                    node_id=node_id,
                )
            )
            return
        locations[node_id] = _NodeLocation(node, path, order)
        order += 1

        if isinstance(node, GroupNode):
            if (
                node.kind not in ("series", "parallel")
                or not isinstance(node.children, tuple)
            ):
                issues.append(
                    _issue(
                        "invalid_document_structure",
                        path,
                        "structure",
                        "Group kind or children are invalid.",
                        node_id=node_id,
                    )
                )
                return
            for index, child in enumerate(node.children):
                walk(child, f"{path}.children[{index}]")
            return

        if (
            not isinstance(node.figure_ref, str)
            or not node.figure_ref
            or not isinstance(node.addons, tuple)
            or any(not isinstance(addon, str) for addon in node.addons)
            or not isinstance(node.anchor, tuple)
            or len(node.anchor) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, Real)
                for value in node.anchor
            )
            or any(
                isinstance(value, float) and not isfinite(value)
                for value in node.anchor
            )
        ):
            issues.append(
                _issue(
                    "invalid_document_structure",
                    path,
                    "structure",
                    "Figure occurrence reference or parameters are invalid.",
                    node_id=node_id,
                    occurrence_id=node_id,
                )
            )
            return
        occurrence_refs.add(node.figure_ref)
        if isinstance(node, CompositeOccurrence):
            if not isinstance(node.root, GroupNode):
                issues.append(
                    _issue(
                        "invalid_document_structure",
                        f"{path}.root",
                        "structure",
                        "Composite occurrence root must be a group.",
                        node_id=node.id,
                        occurrence_id=node.id,
                    )
                )
                return
            walk(node.root, f"{path}.root")

    walk(document.root, "root")
    if unresolved_are_valid and not set(document.unresolved_references).issubset(
        occurrence_refs
    ):
        issues.append(
            _issue(
                "invalid_document_structure",
                "document",
                "structure",
                "Unresolved references must occur in the canonical tree.",
            )
        )
    return locations, issues


def _validate_references_and_capabilities(
    document: DanceDocument,
    locations: dict[str, _NodeLocation],
    repository: object,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    unresolved = set(document.unresolved_references)
    if repository is None:
        return [
            _issue(
                "repository_unavailable",
                "root",
                "figureRef",
                "A figure repository is required for reference validation.",
            )
        ]

    for location in sorted(locations.values(), key=lambda item: item.order):
        node = location.node
        if not isinstance(node, (FigureOccurrence, CompositeOccurrence)):
            continue
        if node.figure_ref in unresolved:
            issues.append(_missing_reference(node, location.path))
            continue

        exists_method = getattr(repository, "figure_exists", None)
        if callable(exists_method):
            try:
                exists = exists_method(node.figure_ref)
            except (FileNotFoundError, KeyError):
                exists = False
            except ValueError as error:
                issues.append(
                    _issue(
                        "invalid_figure_reference",
                        location.path,
                        "figureRef",
                        str(error),
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={"figureRef": node.figure_ref},
                    )
                )
                continue
            if not exists:
                issues.append(_missing_reference(node, location.path))
                continue
        else:
            getter = getattr(repository, "get_definition", None)
            legacy_getter = getattr(repository, "get_legacy_definition", None)
            try:
                if isinstance(node, CompositeOccurrence) and callable(legacy_getter):
                    legacy_getter(node.figure_ref)
                elif callable(getter):
                    getter(node.figure_ref)
                else:
                    issues.append(
                        _issue(
                            "repository_unavailable",
                            location.path,
                            "figureRef",
                            "Figure repository cannot resolve references.",
                            node_id=node.id,
                            occurrence_id=node.id,
                        )
                    )
                    continue
            except (FileNotFoundError, KeyError):
                issues.append(_missing_reference(node, location.path))
                continue
            except ValueError as error:
                issues.append(
                    _issue(
                        "invalid_figure_reference",
                        location.path,
                        "figureRef",
                        str(error),
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={"figureRef": node.figure_ref},
                    )
                )
                continue

        if isinstance(node, CompositeOccurrence):
            legacy_getter = getattr(repository, "get_legacy_definition", None)
            if not callable(legacy_getter):
                issues.append(
                    _issue(
                        "composite_validation_unavailable",
                        location.path,
                        "figureRef",
                        "Figure repository cannot validate composite definitions.",
                        node_id=node.id,
                        occurrence_id=node.id,
                    )
                )
                continue
            try:
                definition = legacy_getter(node.figure_ref)
            except (FileNotFoundError, KeyError):
                issues.append(_missing_reference(node, location.path))
                continue
            except ValueError as error:
                issues.append(
                    _issue(
                        "invalid_composite_reference",
                        location.path,
                        "figureRef",
                        str(error),
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={"figureRef": node.figure_ref},
                    )
                )
                continue
            if not isinstance(definition, dict) or definition.get("Version") != 3:
                issues.append(
                    _issue(
                        "invalid_composite_reference",
                        location.path,
                        "figureRef",
                        "Composite occurrences must reference Version 3 definitions.",
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={
                            "figureRef": node.figure_ref,
                            "definitionVersion": (
                                definition.get("Version")
                                if isinstance(definition, dict)
                                else None
                            ),
                        },
                    )
                )
                continue
            if node.addons:
                issues.append(
                    _issue(
                        "unsupported_addon",
                        f"{location.path}.addons",
                        "addons",
                        "Composite occurrences do not support addon selections.",
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={
                            "figureRef": node.figure_ref,
                            "addons": list(node.addons),
                        },
                    )
                )
            continue

        validate_addons = getattr(repository, "validate_addons", None)
        if callable(validate_addons):
            try:
                validate_addons(
                    node.figure_ref,
                    node.addons,
                    path=location.path,
                    occurrence_id=node.id,
                )
            except AddonValidationError as error:
                issues.append(
                    _issue(
                        error.code,
                        error.path,
                        error.field,
                        error.message,
                        node_id=node.id,
                        occurrence_id=error.occurrence_id or node.id,
                        details={
                            "figureRef": error.figure_ref,
                            "addons": list(error.addons),
                            "dancers": list(error.dancers),
                        },
                    )
                )
            except (FileNotFoundError, KeyError):
                issues.append(_missing_reference(node, location.path))
            except ValueError as error:
                issues.append(
                    _issue(
                        "invalid_figure_definition",
                        location.path,
                        "capabilities",
                        str(error),
                        node_id=node.id,
                        occurrence_id=node.id,
                        details={"figureRef": node.figure_ref},
                    )
                )
        else:
            issues.extend(
                _validate_addons_without_repository_helper(
                    node, location, repository
                )
            )
    return issues


def _validate_addons_without_repository_helper(
    node: FigureOccurrence,
    location: _NodeLocation,
    repository: object,
) -> list[ValidationIssue]:
    getter = getattr(repository, "get_definition", None)
    if not callable(getter):
        return [
            _issue(
                "capability_validation_unavailable",
                f"{location.path}.addons",
                "addons",
                "Figure repository cannot validate addon capabilities.",
                node_id=node.id,
                occurrence_id=node.id,
            )
        ]
    try:
        definition = getter(node.figure_ref)
    except (FileNotFoundError, KeyError):
        return [_missing_reference(node, location.path)]
    except ValueError as error:
        return [
            _issue(
                "invalid_figure_definition",
                location.path,
                "capabilities",
                str(error),
                node_id=node.id,
                occurrence_id=node.id,
                details={"figureRef": node.figure_ref},
            )
        ]
    valid = {
        addon["name"] for addon in getattr(definition, "valid_addons", ())
    }
    for index, addon in enumerate(node.addons):
        if addon not in valid:
            return [
                _issue(
                    "unsupported_addon",
                    f"{location.path}.addons[{index}]",
                    "addons",
                    f"Addon {addon!r} is not supported by figure {node.figure_ref!r}.",
                    node_id=node.id,
                    occurrence_id=node.id,
                    details={"figureRef": node.figure_ref, "addons": list(node.addons)},
                )
            ]
        if addon in node.addons[:index]:
            return [
                _issue(
                    "invalid_addon_selection",
                    f"{location.path}.addons[{index}]",
                    "addons",
                    f"Addon {addon!r} is selected more than once.",
                    node_id=node.id,
                    occurrence_id=node.id,
                    details={"figureRef": node.figure_ref, "addons": list(node.addons)},
                )
            ]
    combinations = getattr(definition, "allowed_addon_combinations", None)
    if combinations is not None and frozenset(node.addons) not in combinations:
        return [
            _issue(
                "invalid_addon_combination",
                f"{location.path}.addons",
                "addons",
                f"Addon combination is not supported by figure {node.figure_ref!r}.",
                node_id=node.id,
                occurrence_id=node.id,
                details={"figureRef": node.figure_ref, "addons": list(node.addons)},
            )
        ]
    return []


def _affected_occurrence_dancers(occurrence, floor) -> list[str]:
    """Name participants at the failed occurrence's proposed start positions."""
    try:
        from src.engine.figures.SimpleFigure import SimpleFigure

        figure = SimpleFigure(
            occurrence.figure_ref,
            list(occurrence.anchor),
            list(occurrence.addons),
        )
    except (FileNotFoundError, OSError, TypeError, ValueError):
        return []

    affected = []
    for index, start in enumerate(figure.StartPos):
        position = tuple(figure.posWithAnchor(start))
        entry = floor.positions.get(position)
        affected.append(
            entry.dancer_name if entry is not None else f"start position {index + 1}"
        )
    return affected


def _missing_reference(
    node: FigureOccurrence | CompositeOccurrence, path: str
) -> ValidationIssue:
    return _issue(
        "reference_not_found",
        path,
        "figureRef",
        f"Figure reference {node.figure_ref!r} could not be resolved.",
        node_id=node.id,
        occurrence_id=node.id,
        details={"figureRef": node.figure_ref},
    )


def _conflict_issues(
    locations: dict[str, _NodeLocation],
    traces: tuple[TraceRecord, ...],
) -> list[ValidationIssue]:
    trace_by_occurrence = {
        record.node_id: record
        for record in traces
        if record.kind == "figure"
    }
    issues: list[ValidationIssue] = []
    for record in traces:
        conflict = record.conflict
        if conflict is None:
            continue
        for position, branch_ids in conflict.conflicts.items():
            competing_writes: list[dict[str, Any]] = []
            first_writer: str | None = None
            for branch_id in branch_ids:
                branch_location = locations.get(branch_id)
                if branch_location is None:
                    continue
                branch_node = branch_location.node
                branch_occurrence_ids = _figure_occurrences(branch_node)
                for occurrence_id in branch_occurrence_ids:
                    occurrence_trace = trace_by_occurrence.get(occurrence_id)
                    if occurrence_trace is None or position not in occurrence_trace.writes:
                        continue
                    first_writer = first_writer or occurrence_id
                    outgoing = occurrence_trace.outgoing_floor
                    incoming = occurrence_trace.incoming_floor
                    entry = (
                        outgoing.positions.get(position)
                        if outgoing is not None
                        else None
                    )
                    if entry is None:
                        entry = incoming.positions.get(position)
                    competing_writes.append(
                        {
                            "occurrenceId": occurrence_id,
                            "dancer": (
                                {
                                    "name": entry.dancer_name,
                                    "gender": entry.dancer_gender,
                                }
                                if entry is not None
                                else None
                            ),
                            "to": (
                                list(position)
                                if outgoing is not None
                                and position in outgoing.positions
                                else None
                            ),
                        }
                    )
            location = (
                locations.get(first_writer)
                if first_writer is not None
                else locations.get(conflict.group_id)
            )
            issues.append(
                _issue(
                    "parallel_conflict",
                    location.path if location else "root",
                    "execution",
                    f"Parallel group {conflict.group_id!r} has competing writes at {position}.",
                    node_id=conflict.group_id,
                    occurrence_id=first_writer,
                    details={
                        "groupId": conflict.group_id,
                        "position": list(position),
                        "dancers": list(dict.fromkeys(
                            write["dancer"]["name"]
                            for write in competing_writes
                            if write["dancer"] is not None
                        )),
                        "competingWrites": competing_writes,
                    },
                )
            )
    return issues


def _figure_occurrences(node: DanceNode) -> tuple[str, ...]:
    if isinstance(node, FigureOccurrence):
        return (node.id,)
    if isinstance(node, CompositeOccurrence):
        return _figure_occurrences(node.root)
    if isinstance(node, GroupNode):
        return tuple(
            occurrence_id
            for child in node.children
            for occurrence_id in _figure_occurrences(child)
        )
    return ()


def _path_for_id(locations: dict[str, _NodeLocation], node_id: str | None) -> str:
    if node_id is None or node_id not in locations:
        return "root"
    return locations[node_id].path


def _issue(
    code: str,
    path: str,
    field: str,
    message: str,
    *,
    node_id: str | None = None,
    occurrence_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity="error",
        path=path,
        node_id=node_id,
        occurrence_id=occurrence_id,
        field=field,
        message=message,
        details=details or {},
    )
