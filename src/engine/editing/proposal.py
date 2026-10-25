"""Public singular module name for proposal operations."""

from src.engine.editing.proposals import (
    Proposal,
    cancel_proposal,
    create_proposal,
)

__all__ = ["Proposal", "cancel_proposal", "create_proposal"]
