"""Semantic editing, structural proposals, transactional commits, and history."""

from src.engine.editing.commands import (
    CreateGroup,
    DeleteNode,
    EditCommandError,
    InsertOccurrence,
    MoveNode,
    ReorderNode,
    UpdateAddons,
    UpdateAnchor,
    apply_command,
)
from src.engine.editing.history import History
from src.engine.editing.proposals import Proposal, cancel_proposal, create_proposal
from src.engine.editing.state import (
    CommitResult,
    EditorState,
    RevisionConflict,
    State,
    StateInitializationError,
    apply_proposal,
    create_state,
)

__all__ = [
    "CommitResult",
    "CreateGroup",
    "DeleteNode",
    "EditCommandError",
    "EditorState",
    "History",
    "InsertOccurrence",
    "MoveNode",
    "Proposal",
    "RevisionConflict",
    "ReorderNode",
    "State",
    "StateInitializationError",
    "UpdateAddons",
    "UpdateAnchor",
    "apply_command",
    "apply_proposal",
    "cancel_proposal",
    "create_proposal",
    "create_state",
]
