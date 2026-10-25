from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from typing import Any, Union


@dataclass(frozen=True)
class FigureOccurrence:
    id: str
    figure_ref: str
    anchor: tuple[Real, Real]
    addons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("Occurrence id must be a non-empty string")
        if not isinstance(self.figure_ref, str) or not self.figure_ref:
            raise ValueError("Figure reference must be a non-empty string")
        if (
            not isinstance(self.anchor, tuple)
            or len(self.anchor) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, Real)
                for value in self.anchor
            )
        ):
            raise ValueError("Occurrence anchor must contain exactly two real numbers")
        if not isinstance(self.addons, tuple) or any(not isinstance(addon, str) for addon in self.addons):
            raise ValueError("Occurrence addons must be a tuple of strings")


@dataclass(frozen=True)
class CompositeOccurrence:
    id: str
    figure_ref: str
    anchor: tuple[Real, Real]
    addons: tuple[str, ...]
    root: GroupNode

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("Composite occurrence id must be a non-empty string")
        if not isinstance(self.figure_ref, str) or not self.figure_ref:
            raise ValueError("Composite figure reference must be a non-empty string")
        if (
            not isinstance(self.anchor, tuple)
            or len(self.anchor) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, Real)
                for value in self.anchor
            )
        ):
            raise ValueError("Composite occurrence anchor must contain two real numbers")
        if not isinstance(self.addons, tuple) or any(
            not isinstance(addon, str) for addon in self.addons
        ):
            raise ValueError("Composite occurrence addons must be a tuple of strings")
        if not isinstance(self.root, GroupNode):
            raise ValueError("Composite occurrence root must be a group")


@dataclass(frozen=True)
class GroupNode:
    id: str
    kind: str
    children: tuple[DanceNode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("Group id must be a non-empty string")
        if self.kind not in ("series", "parallel"):
            raise ValueError("Group kind must be 'series' or 'parallel'")
        if not isinstance(self.children, tuple) or any(
            not isinstance(child, (GroupNode, FigureOccurrence, CompositeOccurrence))
            for child in self.children
        ):
            raise ValueError("Group children must be a tuple of dance nodes")


DanceNode = Union[FigureOccurrence, CompositeOccurrence, GroupNode]


@dataclass(frozen=True)
class DanceDocument:
    format_version: int
    metadata: dict[str, Any]
    root: GroupNode
    incomplete: bool = False
    unresolved_references: tuple[str, ...] = ()
    revision: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.format_version, bool) or self.format_version != 1:
            raise ValueError("Unsupported canonical dance format version")
        if not isinstance(self.metadata, dict):
            raise ValueError("Dance metadata must be an object")
        object.__setattr__(self, "metadata", deepcopy(self.metadata))
        if not isinstance(self.root, GroupNode):
            raise ValueError("Dance root must be a group")
        if not isinstance(self.incomplete, bool):
            raise ValueError("Dance incomplete status must be boolean")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
        ):
            raise ValueError("Dance revision must be a non-negative integer")
        if not isinstance(self.unresolved_references, tuple) or any(
            not isinstance(reference, str) or not reference
            for reference in self.unresolved_references
        ):
            raise ValueError("Unresolved references must be a tuple of non-empty strings")
        if len(set(self.unresolved_references)) != len(self.unresolved_references):
            raise ValueError("Unresolved references must be unique")
        if self.incomplete != bool(self.unresolved_references):
            raise ValueError("Incomplete status must match the unresolved references")

        node_ids: set[str] = set()
        figure_refs: set[str] = set()
        for node in self._walk(self.root):
            if node.id in node_ids:
                raise ValueError(f"Duplicate dance node id: {node.id}")
            node_ids.add(node.id)
            if isinstance(node, (FigureOccurrence, CompositeOccurrence)):
                figure_refs.add(node.figure_ref)
        if not set(self.unresolved_references).issubset(figure_refs):
            raise ValueError("Unresolved references must exist in the dance tree")

    def to_json(self) -> dict[str, Any]:
        return {
            "formatVersion": self.format_version,
            "metadata": deepcopy(self.metadata),
            "status": "incomplete" if self.incomplete else "complete",
            "unresolvedReferences": list(self.unresolved_references),
            "revision": self.revision,
            "root": self._node_to_json(self.root),
        }

    @classmethod
    def from_json(cls, data: Any) -> DanceDocument:
        if not isinstance(data, dict):
            raise ValueError("Canonical dance document must be an object")
        version = data.get("formatVersion")
        if isinstance(version, bool) or version != 1:
            raise ValueError(f"Unsupported canonical dance format version: {version!r}")

        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("Canonical dance metadata must be an object")
        status = data.get("status")
        if status not in ("complete", "incomplete"):
            raise ValueError("Canonical dance status must be 'complete' or 'incomplete'")
        unresolved = data.get("unresolvedReferences")
        if not isinstance(unresolved, list):
            raise ValueError("unresolvedReferences must be an array")
        revision = data.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError("Dance revision must be a non-negative integer")

        return cls(
            format_version=version,
            metadata=deepcopy(metadata),
            root=cls._node_from_json(data.get("root")),
            incomplete=status == "incomplete",
            unresolved_references=tuple(unresolved),
            revision=revision,
        )

    def find_node(self, node_id: str) -> DanceNode:
        for node in self._walk(self.root):
            if node.id == node_id:
                return node
        raise KeyError(node_id)

    @staticmethod
    def _walk(node: DanceNode):
        yield node
        if isinstance(node, GroupNode):
            for child in node.children:
                yield from DanceDocument._walk(child)
        elif isinstance(node, CompositeOccurrence):
            yield from DanceDocument._walk(node.root)

    @classmethod
    def _node_to_json(cls, node: DanceNode) -> dict[str, Any]:
        if isinstance(node, CompositeOccurrence):
            return {
                "type": "compositeOccurrence",
                "id": node.id,
                "figureRef": node.figure_ref,
                "anchor": list(node.anchor),
                "addons": list(node.addons),
                "root": cls._node_to_json(node.root),
            }
        if isinstance(node, FigureOccurrence):
            return {
                "type": "figure",
                "id": node.id,
                "figureRef": node.figure_ref,
                "anchor": list(node.anchor),
                "addons": list(node.addons),
            }
        return {
            "type": "group",
            "id": node.id,
            "kind": node.kind,
            "children": [cls._node_to_json(child) for child in node.children],
        }

    @classmethod
    def _node_from_json(cls, data: Any) -> DanceNode:
        if not isinstance(data, dict):
            raise ValueError("Dance nodes must be objects")
        node_type = data.get("type")
        node_id = data.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Dance node id must be a non-empty string")
        if node_type == "compositeOccurrence":
            anchor, addons = cls._parse_occurrence_parameters(data)
            return CompositeOccurrence(
                id=node_id,
                figure_ref=data.get("figureRef"),
                anchor=anchor,
                addons=addons,
                root=cls._node_from_json(data.get("root")),
            )
        if node_type == "figure":
            anchor, addons = cls._parse_occurrence_parameters(data)
            figure_ref = data.get("figureRef")
            return FigureOccurrence(
                id=node_id,
                figure_ref=figure_ref,
                anchor=anchor,
                addons=addons,
            )
        if node_type == "group":
            children = data.get("children")
            if not isinstance(children, list):
                raise ValueError("Group node children must be an array")
            return GroupNode(
                id=node_id,
                kind=data.get("kind"),
                children=tuple(cls._node_from_json(child) for child in children),
            )
        raise ValueError(f"Unsupported dance node type: {node_type!r}")

    @staticmethod
    def _parse_occurrence_parameters(data: dict[str, Any]) -> tuple[tuple[Real, Real], tuple[str, ...]]:
        anchor = data.get("anchor")
        addons = data.get("addons")
        if (
            not isinstance(anchor, list)
            or len(anchor) != 2
            or any(isinstance(value, bool) or not isinstance(value, Real) for value in anchor)
        ):
            raise ValueError("Figure occurrence anchor must contain two real numbers")
        if not isinstance(addons, list) or any(not isinstance(addon, str) for addon in addons):
            raise ValueError("Figure occurrence addons must be an array of strings")
        return (anchor[0], anchor[1]), tuple(addons)
