"""Immutable current-document state and atomic proposal commits."""

from __future__ import annotations

from dataclasses import dataclass, replace

from src.engine.domain.dance_model import DanceDocument
from src.engine.execution.combine import FloorState
from src.engine.execution.executor import ExecutionResult, execute_document
from src.engine.validation import ValidationReport, validate_document

from src.engine.editing.proposals import Proposal


@dataclass(frozen=True)
class EditorState:
    document: DanceDocument
    execution_result: ExecutionResult
    initial_floor: FloorState
    repository: object

    @property
    def trace(self):
        return self.execution_result.trace_records


State = EditorState


class StateInitializationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        super().__init__(
            report.first_blocking.message
            if report.first_blocking is not None
            else "Initial document is invalid."
        )


@dataclass(frozen=True)
class RevisionConflict:
    code: str
    expected_revision: int
    actual_revision: int
    message: str = "Proposal was created from a stale document revision."


@dataclass(frozen=True)
class CommitResult:
    accepted: bool
    state: EditorState
    validation: ValidationReport | None = None
    conflict: RevisionConflict | None = None

    @property
    def rejection(self) -> ValidationReport | None:
        return self.validation if not self.accepted else None


def create_state(
    document: DanceDocument,
    initial_floor: FloorState | object,
    repository: object,
) -> EditorState:
    floor = (
        initial_floor
        if isinstance(initial_floor, FloorState)
        else FloorState.from_legacy(initial_floor)
    )
    report = validate_document(document, floor, repository)
    if not report.is_valid:
        raise StateInitializationError(report)
    execution = execute_document(document, floor, repository)
    return EditorState(document, execution, floor, repository)


def apply_proposal(state: EditorState, proposal: Proposal) -> CommitResult:
    candidate = proposal.candidate
    if (
        proposal.base_revision != state.document.revision
        or candidate.revision != proposal.base_revision
    ):
        return CommitResult(
            accepted=False,
            state=state,
            conflict=RevisionConflict(
                "revision_conflict",
                proposal.base_revision,
                (
                    candidate.revision
                    if candidate.revision != proposal.base_revision
                    else state.document.revision
                ),
            ),
        )

    report = validate_document(candidate, state.initial_floor, state.repository)
    if not report.is_valid:
        return CommitResult(
            accepted=False,
            state=state,
            validation=report,
        )

    committed_document = replace(
        candidate, revision=state.document.revision + 1
    )
    execution = execute_document(
        committed_document, state.initial_floor, state.repository
    )
    committed = EditorState(
        committed_document, execution, state.initial_floor, state.repository
    )
    return CommitResult(accepted=True, state=committed, validation=report)
