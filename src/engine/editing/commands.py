"""Pure semantic edits for canonical dance documents."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Optional, Union
from uuid import uuid4

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    FigureOccurrence,
    GroupNode,
)
from src.engine.domain.legacy_adapter import LegacyDanceAdapter


class EditCommandError(ValueError):
    """A semantic edit that cannot be applied to the supplied document."""

    def __init__(
        self, code: str, message: str, *, node_id: str | None = None, path: str = ""
    ) -> None:
        self.code = code
        self.node_id = node_id
        self.path = path
        super().__init__(message)


@dataclass(frozen=True)
class InsertOccurrence:
    parent_group_id: str
    figure_ref: str
    index: int
    anchor: tuple[Real, Real] = (0, 0)
    addons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeleteNode:
    node_id: str


@dataclass(frozen=True)
class ReorderNode:
    node_id: str
    index: int


@dataclass(frozen=True)
class MoveNode:
    node_id: str
    destination_group_id: str
    index: int


@dataclass(frozen=True)
class UpdateAnchor:
    node_id: str
    anchor: tuple[Real, Real]


@dataclass(frozen=True)
class UpdateAddons:
    node_id: str
    addons: tuple[str, ...]


@dataclass(frozen=True)
class UpdateOccurrence:
    """Update anchor and add-ons of one occurrence as a single semantic edit."""

    node_id: str
    anchor: tuple[Real, Real]
    addons: tuple[str, ...]


@dataclass(frozen=True)
class CreateGroup:
    parent_group_id: str
    kind: str
    index: int


Command = Union[
    UpdateOccurrence,
    InsertOccurrence,
    DeleteNode,
    ReorderNode,
    MoveNode,
    UpdateAnchor,
    UpdateAddons,
    CreateGroup,
]


def apply_command(
    document: DanceDocument, command: Command, repository: Optional[object] = None
) -> DanceDocument:
    """Return a new document with one semantic command applied."""
    if not isinstance(document, DanceDocument):
        raise EditCommandError("invalid_document", "Expected a canonical DanceDocument.")
    inserted_unresolved = ()
    if isinstance(command, UpdateOccurrence):
        with_anchor = apply_command(
            document, UpdateAnchor(command.node_id, command.anchor), repository
        )
        return apply_command(
            with_anchor, UpdateAddons(command.node_id, command.addons), repository
        )
    if isinstance(command, InsertOccurrence):
        parent = _require_group(document.root, command.parent_group_id)
        if parent.kind != "series":
            raise EditCommandError(
                "insert_requires_series",
                "New occurrences may be inserted directly into a series group.",
                node_id=parent.id,
            )
        _validate_insert(command)
        _validate_index(command.index, len(parent.children), insertion=True)
        inserted, inserted_unresolved = _new_catalog_occurrence(command, repository)
        root = _edit_group(
            document.root,
            command.parent_group_id,
            lambda group: _with_child_inserted(group, command.index, inserted),
        )
    elif isinstance(command, DeleteNode):
        node, parent = _find_node_and_parent(document.root, command.node_id)
        if not isinstance(node, (FigureOccurrence, CompositeOccurrence)) or parent is None:
            raise EditCommandError(
                "delete_requires_occurrence",
                "Only a figure occurrence can be deleted; groups and the root cannot.",
                node_id=command.node_id,
            )
        root = _edit_group(
            document.root,
            parent.id,
            lambda group: _with_children(
                group, tuple(child for child in group.children if child.id != node.id)
            ),
        )
    elif isinstance(command, ReorderNode):
        node, parent = _find_node_and_parent(document.root, command.node_id)
        if parent is None or parent.kind != "series":
            raise EditCommandError(
                "reorder_requires_series",
                "Reordering is limited to siblings in a series group.",
                node_id=command.node_id,
            )
        _validate_index(command.index, len(parent.children))
        source_index = next(
            index for index, child in enumerate(parent.children) if child.id == node.id
        )
        if source_index == command.index:
            return document
        children = list(parent.children)
        children.insert(command.index, children.pop(source_index))
        root = _edit_group(
            document.root, parent.id, lambda group: _with_children(group, tuple(children))
        )
    elif isinstance(command, MoveNode):
        node, parent = _find_node_and_parent(document.root, command.node_id)
        if not isinstance(node, (FigureOccurrence, CompositeOccurrence)) or parent is None:
            raise EditCommandError(
                "move_requires_occurrence",
                "Only a figure or composite occurrence can be moved.",
                node_id=command.node_id,
            )
        try:
            destination = _require_group(document.root, command.destination_group_id)
        except EditCommandError as error:
            if error.code == "node_not_found":
                raise EditCommandError(
                    "destination_not_found",
                    f"Destination group {command.destination_group_id!r} was not found.",
                    node_id=command.destination_group_id,
                ) from error
            raise
        if any(descendant.id == destination.id for descendant in _walk(node)):
            raise EditCommandError(
                "invalid_destination",
                "An occurrence cannot be moved into its own subtree.",
                node_id=command.node_id,
            )
        same_parent = parent.id == destination.id
        destination_size = len(destination.children) - int(same_parent)
        _validate_index(command.index, destination_size, insertion=True)
        removed_root = _edit_group(
            document.root,
            parent.id,
            lambda group: _with_children(
                group, tuple(child for child in group.children if child.id != node.id)
            ),
        )
        root = _edit_group(
            removed_root,
            command.destination_group_id,
            lambda group: _with_child_inserted(group, command.index, node),
        )
    elif isinstance(command, UpdateAnchor):
        _validate_anchor(command.anchor)
        node = _require_occurrence(document.root, command.node_id)
        root = _replace_node(
            document.root, node.id, lambda current: _with_anchor(current, command.anchor)
        )
    elif isinstance(command, UpdateAddons):
        if not isinstance(command.addons, tuple) or any(
            not isinstance(addon, str) for addon in command.addons
        ):
            raise EditCommandError(
                "invalid_addon_selection",
                "Addon selections must be a tuple of strings.",
                node_id=command.node_id,
            )
        node = _require_occurrence(document.root, command.node_id)
        if isinstance(node, CompositeOccurrence) and command.addons:
            raise EditCommandError(
                "composite_addons_unsupported",
                "Non-empty addons are not supported on Version 3 composite occurrences.",
                node_id=command.node_id,
            )
        root = _replace_node(
            document.root, node.id, lambda current: _with_addons(current, command.addons)
        )
    elif isinstance(command, CreateGroup):
        parent = _require_group(document.root, command.parent_group_id)
        if command.kind not in ("series", "parallel"):
            raise EditCommandError(
                "invalid_group_kind", "New groups must be series or parallel."
            )
        _validate_index(command.index, len(parent.children), insertion=True)
        group = GroupNode(_new_id(), command.kind, ())
        root = _edit_group(
            document.root,
            command.parent_group_id,
            lambda current: _with_child_inserted(current, command.index, group),
        )
    else:
        raise EditCommandError("unsupported_command", "Unsupported semantic edit command.")

    unresolved = tuple(
        reference
        for reference in document.unresolved_references
        if any(
            isinstance(node, (FigureOccurrence, CompositeOccurrence))
            and node.figure_ref == reference
            for node in _walk(root)
        )
    )
    unresolved = tuple(dict.fromkeys(unresolved + inserted_unresolved))
    return DanceDocument(
        format_version=document.format_version,
        metadata=document.metadata,
        root=root,
        incomplete=bool(unresolved),
        unresolved_references=unresolved,
        revision=document.revision,
    )


def _new_catalog_occurrence(
    command: InsertOccurrence, repository: Optional[object]
) -> tuple[Union[FigureOccurrence, CompositeOccurrence], tuple[str, ...]]:
    get_definition = getattr(repository, "get_legacy_definition", None)
    reference_exists = getattr(repository, "figure_exists", None)
    if repository is None or not callable(get_definition):
        raise EditCommandError(
            "repository_required",
            "A figure repository is required to insert a catalog occurrence.",
        )

    if callable(reference_exists):
        try:
            exists = reference_exists(command.figure_ref)
        except ValueError as error:
            raise EditCommandError(
                "invalid_figure_reference", str(error)
            ) from error
        if not exists:
            raise EditCommandError(
                "reference_not_found",
                f"Figure reference {command.figure_ref!r} is not in the catalog.",
            )
    try:
        definition = get_definition(command.figure_ref)
    except FileNotFoundError:
        raise EditCommandError(
            "reference_not_found",
            f"Figure reference {command.figure_ref!r} is not in the catalog.",
        ) from None
    except ValueError as error:
        raise EditCommandError(
            "invalid_figure_definition", str(error)
        ) from error
    if not isinstance(definition, dict):
        raise EditCommandError(
            "invalid_figure_definition",
            f"Figure definition for {command.figure_ref!r} must be an object.",
        )

    version = definition.get("Version")
    if version == 2:
        return (
            FigureOccurrence(
                _new_id(), command.figure_ref, command.anchor, command.addons
            ),
            (),
        )
    if version != 3:
        raise EditCommandError(
            "unsupported_figure_version",
            f"Figure definition for {command.figure_ref!r} has unsupported version.",
        )

    if not callable(reference_exists):
        raise EditCommandError(
            "repository_required",
            "A repository with figure_exists is required to resolve composite children.",
        )
    try:
        embedded_document = LegacyDanceAdapter.from_data(
            {"Version": 3, "FigureList": definition.get("FigureList")},
            reference_exists,
            get_definition=get_definition,
        )
    except ValueError as error:
        raise EditCommandError(
            "invalid_composite_definition", str(error)
        ) from error
    return (
        CompositeOccurrence(
            _new_id(),
            command.figure_ref,
            command.anchor,
            command.addons,
            embedded_document.root,
        ),
        embedded_document.unresolved_references,
    )


def _validate_insert(command: InsertOccurrence) -> None:
    if not isinstance(command.figure_ref, str) or not command.figure_ref:
        raise EditCommandError("invalid_figure_reference", "Figure reference is required.")
    _validate_anchor(command.anchor)
    if not isinstance(command.addons, tuple) or any(
        not isinstance(addon, str) for addon in command.addons
    ):
        raise EditCommandError(
            "invalid_addon_selection", "Addon selections must be a tuple of strings."
        )


def _validate_anchor(anchor: object) -> None:
    if (
        not isinstance(anchor, tuple)
        or len(anchor) != 2
        or any(isinstance(value, bool) or not isinstance(value, Real) for value in anchor)
        or any(isinstance(value, float) and not isfinite(value) for value in anchor)
    ):
        raise EditCommandError(
            "invalid_anchor", "Anchor must contain exactly two finite real numbers."
        )


def _validate_index(index: object, size: int, *, insertion: bool = False) -> None:
    maximum = size if insertion else size - 1
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= maximum:
        raise EditCommandError(
            "invalid_index",
            f"Index must be between 0 and {maximum}.",
        )


def _new_id() -> str:
    return str(uuid4())


def _require_group(root: GroupNode, node_id: str) -> GroupNode:
    node = _find_node(root, node_id)
    if not isinstance(node, GroupNode):
        raise EditCommandError(
            "destination_not_group",
            "The requested parent or destination must be a group.",
            node_id=node_id,
        )
    return node


def _require_occurrence(
    root: GroupNode, node_id: str
) -> FigureOccurrence | CompositeOccurrence:
    node = _find_node(root, node_id)
    if not isinstance(node, (FigureOccurrence, CompositeOccurrence)):
        raise EditCommandError(
            "target_requires_occurrence",
            "The requested target must be a figure occurrence.",
            node_id=node_id,
        )
    return node


def _find_node(root: DanceNode, node_id: str) -> DanceNode:
    for node in _walk(root):
        if node.id == node_id:
            return node
    raise EditCommandError(
        "node_not_found", f"Dance node {node_id!r} was not found.", node_id=node_id
    )


def _find_node_and_parent(
    root: GroupNode, node_id: str
) -> tuple[DanceNode, GroupNode | None]:
    if root.id == node_id:
        return root, None

    def search(node: DanceNode) -> tuple[DanceNode, GroupNode] | None:
        if isinstance(node, GroupNode):
            for child in node.children:
                if child.id == node_id:
                    return child, node
                result = search(child)
                if result:
                    return result
        elif isinstance(node, CompositeOccurrence):
            if node.root.id == node_id:
                return node.root, None  # Embedded root is not an editable sibling.
            result = search(node.root)
            if result:
                return result
        return None

    found = search(root)
    if found is None:
        raise EditCommandError(
            "node_not_found", f"Dance node {node_id!r} was not found.", node_id=node_id
        )
    return found


def _walk(node: DanceNode):
    yield node
    if isinstance(node, GroupNode):
        for child in node.children:
            yield from _walk(child)
    elif isinstance(node, CompositeOccurrence):
        yield from _walk(node.root)


def _edit_group(
    node: GroupNode, group_id: str, edit
) -> GroupNode:
    if node.id == group_id:
        return edit(node)
    children: list[DanceNode] = []
    changed = False
    for child in node.children:
        if isinstance(child, GroupNode):
            replacement = _edit_group(child, group_id, edit)
        elif isinstance(child, CompositeOccurrence):
            replacement_root = _edit_group(child.root, group_id, edit)
            replacement = (
                CompositeOccurrence(
                    child.id,
                    child.figure_ref,
                    child.anchor,
                    child.addons,
                    replacement_root,
                )
                if replacement_root is not child.root
                else child
            )
        else:
            replacement = child
        children.append(replacement)
        changed |= replacement is not child
    return _with_children(node, tuple(children)) if changed else node


def _replace_node(node: DanceNode, node_id: str, edit) -> DanceNode:
    if node.id == node_id:
        return edit(node)
    if isinstance(node, GroupNode):
        children = tuple(_replace_node(child, node_id, edit) for child in node.children)
        return _with_children(node, children) if any(
            new is not old for new, old in zip(children, node.children)
        ) else node
    if isinstance(node, CompositeOccurrence):
        root = _replace_node(node.root, node_id, edit)
        if root is not node.root:
            return CompositeOccurrence(
                node.id, node.figure_ref, node.anchor, node.addons, root
            )
    return node


def _with_child_inserted(
    group: GroupNode, index: int, child: DanceNode
) -> GroupNode:
    children = list(group.children)
    children.insert(index, child)
    return _with_children(group, tuple(children))


def _with_children(group: GroupNode, children: tuple[DanceNode, ...]) -> GroupNode:
    return group if children is group.children else GroupNode(group.id, group.kind, children)


def _with_anchor(
    node: DanceNode, anchor: tuple[Real, Real]
) -> DanceNode:
    if isinstance(node, FigureOccurrence):
        return FigureOccurrence(node.id, node.figure_ref, anchor, node.addons)
    return CompositeOccurrence(
        node.id, node.figure_ref, anchor, node.addons, node.root
    )


def _with_addons(node: DanceNode, addons: tuple[str, ...]) -> DanceNode:
    if isinstance(node, FigureOccurrence):
        return FigureOccurrence(node.id, node.figure_ref, node.anchor, addons)
    return CompositeOccurrence(
        node.id, node.figure_ref, node.anchor, addons, node.root
    )
