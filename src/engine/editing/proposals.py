"""Structural proposals; deliberately independent of validation and execution."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Optional

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    GroupNode,
)
from src.engine.editing.commands import Command, apply_command


@dataclass(frozen=True, init=False)
class Proposal:
    _candidate: DanceDocument
    base_revision: int
    _structural_tree: dict[str, Any]

    def __init__(
        self, candidate: DanceDocument, base_revision: int, structural_tree: dict[str, Any]
    ) -> None:
        if candidate.revision != base_revision:
            raise ValueError(
                "Proposal base revision must match the source document revision."
            )
        object.__setattr__(
            self,
            "_candidate",
            DanceDocument.from_json(candidate.to_json()),
        )
        object.__setattr__(self, "base_revision", base_revision)
        object.__setattr__(self, "_structural_tree", deepcopy(structural_tree))

    @property
    def candidate(self) -> DanceDocument:
        return DanceDocument.from_json(self._candidate.to_json())

    @property
    def document(self) -> DanceDocument:
        return self.candidate

    @property
    def structural_tree(self) -> dict[str, Any]:
        return deepcopy(self._structural_tree)

    @property
    def tree(self) -> dict[str, Any]:
        return self.structural_tree


def create_proposal(
    document: DanceDocument,
    command: Command,
    base_revision: int,
    repository: Optional[object] = None,
) -> Proposal:
    if isinstance(base_revision, bool) or not isinstance(base_revision, int) or base_revision < 0:
        raise ValueError("Proposal base revision must be a non-negative integer.")
    if base_revision != document.revision:
        raise ValueError("Proposal base revision must match the source document revision.")
    candidate = apply_command(document, command, repository=repository)
    return Proposal(candidate, base_revision, _project(candidate.root, "root"))


def _project(node: DanceNode, path: str) -> dict[str, Any]:
    if isinstance(node, GroupNode):
        return {
            "type": "group",
            "id": node.id,
            "kind": node.kind,
            "path": path,
            "children": [
                _project(child, f"{path}.children[{index}]")
                for index, child in enumerate(node.children)
            ],
        }
    if isinstance(node, CompositeOccurrence):
        return {
            "type": "compositeOccurrence",
            "id": node.id,
            "figureRef": node.figure_ref,
            "anchor": list(node.anchor),
            "addons": list(node.addons),
            "path": path,
            "root": _project(node.root, f"{path}.root"),
        }
    return {
        "type": "figureOccurrence",
        "id": node.id,
        "figureRef": node.figure_ref,
        "anchor": list(node.anchor),
        "addons": list(node.addons),
        "path": path,
    }


def cancel_proposal(proposal: Proposal) -> None:
    """Discard a proposal without touching a document or history."""
    return None
