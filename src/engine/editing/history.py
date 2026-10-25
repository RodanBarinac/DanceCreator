"""Undo/redo history for accepted semantic edits and their execution traces."""

from __future__ import annotations

from dataclasses import replace

from src.engine.editing.proposals import Proposal, cancel_proposal
from src.engine.editing.state import CommitResult, EditorState, apply_proposal


class History:
    def __init__(self, state: EditorState) -> None:
        self._state = state
        self._undo: list[EditorState] = []
        self._redo: list[EditorState] = []

    @property
    def state(self) -> EditorState:
        return self._state

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    @property
    def redo_depth(self) -> int:
        return len(self._redo)

    def apply(self, proposal: Proposal) -> CommitResult:
        result = apply_proposal(self._state, proposal)
        if result.accepted:
            self._undo.append(self._state)
            self._state = result.state
            self._redo.clear()
            return CommitResult(True, self._state, result.validation)
        return result

    def save(self, state: EditorState) -> EditorState:
        """Record a saved document without discarding accepted edit history."""
        previous = self._state.document.to_json()
        current = state.document.to_json()
        previous.pop("revision", None)
        current.pop("revision", None)
        if previous != current:
            self._undo.append(self._state)
            self._redo.clear()
        self._state = state
        return self._state

    def cancel(self, proposal: Proposal) -> None:
        return cancel_proposal(proposal)

    def undo(self) -> EditorState:
        if not self._undo:
            raise RuntimeError("No edit available to undo.")
        self._redo.append(self._state)
        previous = self._undo.pop()
        self._state = _restore(previous, self._state.document.revision + 1)
        return self._state

    def redo(self) -> EditorState:
        if not self._redo:
            raise RuntimeError("No edit available to redo.")
        self._undo.append(self._state)
        following = self._redo.pop()
        self._state = _restore(following, self._state.document.revision + 1)
        return self._state


def _restore(state: EditorState, revision: int) -> EditorState:
    return EditorState(
        replace(state.document, revision=revision),
        state.execution_result,
        state.initial_floor,
        state.repository,
    )
