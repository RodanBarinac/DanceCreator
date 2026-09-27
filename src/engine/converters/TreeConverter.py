"""
Tree converter utilities.

Converts jsTree API payloads back into the recursive Dance.FigureList format
used by dance JSON files.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


class TreeConversionError(Exception):
    """Raised when a jsTree payload cannot be converted into a FigureList."""

    def __init__(self, message: str, node_id: Optional[str] = None):
        self.message = message
        self.node_id = node_id
        if node_id is None:
            super().__init__(message)
        else:
            super().__init__(f"{message} (node_id={node_id})")


class TreeConverter:
    """Converts validated jsTree nodes into Dance.FigureList data."""

    DEFAULT_ANCHOR = [1, 1]
    MAX_DEPTH = 50
    GROUP_TYPES = {"s", "p"}
    NODE_TYPES = {"root", "group", "figure"}

    @classmethod
    def jstree_to_figure_list(cls, tree_node: Dict[str, Any]) -> List[Any]:
        """
        Convert a jsTree root node into the recursive Dance.FigureList format.

        Root nodes default to a sequential top-level group unless
        data.groupType is provided. For compatibility with the existing
        build_dance_tree() GET helper, a root node with no type and a single
        group child is treated as that child group directly.
        """
        return cls._convert_root(tree_node, depth=0, active_nodes=set())

    @classmethod
    def validate_round_trip(cls, original_dance: Dict[str, Any]) -> bool:
        """Build a tree with the GUI helper and verify conversion round-trips."""
        import GUI_DanceCreator_App as app_module

        dance_for_tree = dict(original_dance)
        dance_for_tree["FigureList"] = cls._prepare_group_for_tree_builder(original_dance.get("FigureList"))
        tree = app_module.build_dance_tree(
            dance_for_tree,
            original_dance.get("Name", "Dance") if isinstance(original_dance, dict) else "Dance",
        )
        converted = cls.jstree_to_figure_list(tree)
        expected = cls._normalize_group(original_dance.get("FigureList"))
        actual = cls._normalize_group(converted)
        return expected == actual

    @classmethod
    def _convert_root(
        cls,
        node: Dict[str, Any],
        depth: int,
        active_nodes: Set[int],
    ) -> List[Any]:
        cls._ensure_depth(depth, cls._node_id(node))
        cls._ensure_node_dict(node)

        node_id = cls._node_id(node)
        entered = cls._enter_node(node, active_nodes, node_id)
        try:
            node_type = node.get("type")
            if node_type not in (None, "root"):
                raise TreeConversionError(f"Invalid root node type: {node_type!r}", node_id=node_id)

            children = node.get("children")
            if not isinstance(children, list):
                raise TreeConversionError("Root node must include a children list", node_id=node_id)

            root_group_type = cls._extract_root_group_type(node, node_id)

            if (
                node_type is None
                and root_group_type is None
                and len(children) == 1
                and isinstance(children[0], dict)
                and children[0].get("type") == "group"
            ):
                return cls._convert_element(children[0], depth + 1, active_nodes)

            return [
                root_group_type or "s",
                [cls._convert_element(child, depth + 1, active_nodes) for child in children],
            ]
        finally:
            active_nodes.discard(entered)

    @classmethod
    def _convert_element(
        cls,
        node: Dict[str, Any],
        depth: int,
        active_nodes: Set[int],
    ) -> List[Any]:
        cls._ensure_depth(depth, cls._node_id(node))
        cls._ensure_node_dict(node)

        node_id = cls._node_id(node)
        entered = cls._enter_node(node, active_nodes, node_id)
        try:
            node_type = node.get("type")
            if node_type == "group":
                return cls._convert_group(node, depth, active_nodes)
            if node_type == "figure":
                return cls._convert_figure(node, node_id)
            raise TreeConversionError(f"Invalid node type: {node_type!r}", node_id=node_id)
        finally:
            active_nodes.discard(entered)

    @classmethod
    def _convert_group(
        cls,
        node: Dict[str, Any],
        depth: int,
        active_nodes: Set[int],
    ) -> List[Any]:
        node_id = cls._node_id(node)
        data = cls._get_data(node, node_id)
        group_type = data.get("groupType")
        if group_type not in cls.GROUP_TYPES:
            raise TreeConversionError("Group node must define groupType 's' or 'p'", node_id=node_id)

        children = node.get("children")
        if not isinstance(children, list):
            raise TreeConversionError("Group node must include a children list", node_id=node_id)

        return [
            group_type,
            [cls._convert_element(child, depth + 1, active_nodes) for child in children],
        ]

    @classmethod
    def _convert_figure(cls, node: Dict[str, Any], node_id: Optional[str]) -> List[Any]:
        data = cls._get_data(node, node_id)

        figure_name = data.get("figureName")
        if not isinstance(figure_name, str) or not figure_name.strip():
            raise TreeConversionError("Figure node must define a non-empty figureName", node_id=node_id)

        anchor = cls._normalize_anchor(data.get("anchor"))
        addons = cls._normalize_addons(data.get("addons"), node_id)

        target: Any = figure_name.strip()
        if addons:
            target = [target, addons]

        return [anchor, target]

    @classmethod
    def _extract_root_group_type(
        cls,
        node: Dict[str, Any],
        node_id: Optional[str],
    ) -> Optional[str]:
        data = cls._get_data(node, node_id, default={})
        if "groupType" not in data:
            return None

        group_type = data.get("groupType")
        if group_type not in cls.GROUP_TYPES:
            raise TreeConversionError("Root node groupType must be 's' or 'p'", node_id=node_id)
        return group_type

    @classmethod
    def _get_data(
        cls,
        node: Dict[str, Any],
        node_id: Optional[str],
        default: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if "data" not in node:
            return {} if default is None else dict(default)

        data = node.get("data")
        if data is None:
            return {} if default is None else dict(default)
        if not isinstance(data, dict):
            raise TreeConversionError("Node data must be an object", node_id=node_id)
        return data

    @classmethod
    def _normalize_anchor(cls, anchor: Any) -> List[int]:
        if not isinstance(anchor, (list, tuple)) or len(anchor) < 2:
            return list(cls.DEFAULT_ANCHOR)

        row = cls._coerce_anchor_value(anchor[0])
        col = cls._coerce_anchor_value(anchor[1])
        return [row, col]

    @classmethod
    def _coerce_anchor_value(cls, value: Any) -> int:
        if isinstance(value, bool):
            return 1
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            return 1
        if coerced < 1:
            return 1
        return coerced

    @classmethod
    def _normalize_addons(cls, addons: Any, node_id: Optional[str]) -> List[str]:
        if addons is None:
            return []

        if isinstance(addons, list) and len(addons) == 1 and isinstance(addons[0], list):
            addons = addons[0]

        if not isinstance(addons, list):
            raise TreeConversionError("Figure addons must be an array", node_id=node_id)

        normalized = []
        for addon in addons:
            if not isinstance(addon, str):
                raise TreeConversionError("Figure addons must contain only strings", node_id=node_id)
            normalized.append(addon)
        return normalized

    @classmethod
    def _enter_node(cls, node: Dict[str, Any], active_nodes: Set[int], node_id: Optional[str]) -> int:
        node_ref = id(node)
        if node_ref in active_nodes:
            raise TreeConversionError("Circular tree reference detected", node_id=node_id)
        active_nodes.add(node_ref)
        return node_ref

    @classmethod
    def _ensure_depth(cls, depth: int, node_id: Optional[str]) -> None:
        if depth > cls.MAX_DEPTH:
            raise TreeConversionError(
                f"Maximum tree depth of {cls.MAX_DEPTH} exceeded",
                node_id=node_id,
            )

    @classmethod
    def _ensure_node_dict(cls, node: Any) -> None:
        if not isinstance(node, dict):
            raise TreeConversionError("Tree nodes must be objects")

    @classmethod
    def _node_id(cls, node: Any) -> Optional[str]:
        if not isinstance(node, dict):
            return None
        if "id" not in node:
            return None
        return str(node.get("id"))

    @classmethod
    def _normalize_group(cls, value: Any) -> Any:
        if not isinstance(value, list) or len(value) != 2:
            return value

        head, tail = value
        if isinstance(head, str) and head in cls.GROUP_TYPES and isinstance(tail, list):
            return [head, [cls._normalize_group(item) for item in tail]]

        if isinstance(head, list) and len(head) == 2:
            anchor = cls._normalize_anchor(head)
            target = cls._normalize_target(tail)
            return [anchor, target]

        return value

    @classmethod
    def _normalize_target(cls, target: Any) -> Any:
        if isinstance(target, str):
            return [target, []]

        if isinstance(target, list) and len(target) == 2 and isinstance(target[0], str) and isinstance(target[1], list):
            return [target[0], target[1]]

        if isinstance(target, list) and target:
            name = target[0]
            if not isinstance(name, str):
                return target

            addons = []
            if len(target) == 2 and isinstance(target[1], list):
                addons = target[1]
            else:
                addons = target[1:]
            return [name, addons]

        return target

    @classmethod
    def _prepare_group_for_tree_builder(cls, value: Any) -> Any:
        if not isinstance(value, list) or len(value) != 2:
            return value

        head, tail = value
        if isinstance(head, str) and head in cls.GROUP_TYPES and isinstance(tail, list):
            return [head, [cls._prepare_group_for_tree_builder(item) for item in tail]]

        if isinstance(head, list) and len(head) == 2:
            target = tail
            if isinstance(target, str):
                return [cls._normalize_anchor(head), [target, []]]
            if isinstance(target, list) and len(target) == 2 and isinstance(target[0], str) and isinstance(target[1], list):
                return [cls._normalize_anchor(head), [target[0], list(target[1])]]

        return value
