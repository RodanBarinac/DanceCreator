from __future__ import annotations

import json
from copy import deepcopy
from numbers import Real
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    FigureOccurrence,
    GroupNode,
)


class LegacyDanceAdapter:
    """Reads legacy dance documents without modifying their source representation."""

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        reference_exists: Callable[[str], bool],
        get_definition: Callable[[str], Any] | None = None,
    ) -> DanceDocument:
        with Path(path).open("r", encoding="utf-8-sig") as source:
            return cls.from_data(
                json.load(source),
                reference_exists,
                get_definition=get_definition,
            )

    @classmethod
    def from_data(
        cls,
        data: Any,
        reference_exists: Callable[[str], bool],
        get_definition: Callable[[str], Any] | None = None,
    ) -> DanceDocument:
        if not isinstance(data, dict):
            raise ValueError("Legacy dance document must be an object")
        if data.get("Version") not in (2, 3):
            raise ValueError(f"Unsupported legacy dance version: {data.get('Version')!r}")
        if not callable(reference_exists):
            raise TypeError("reference_exists must be callable")

        unresolved: list[str] = []
        root = cls._parse_node(
            data.get("FigureList"),
            reference_exists,
            unresolved,
            get_definition,
        )
        if not isinstance(root, GroupNode):
            raise ValueError("Legacy FigureList must have a series or parallel group root")
        metadata = deepcopy(
            {key: value for key, value in data.items() if key not in ("Version", "FigureList")}
        )
        return DanceDocument(
            format_version=1,
            metadata=metadata,
            root=root,
            incomplete=bool(unresolved),
            unresolved_references=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _parse_node(
        cls,
        value: Any,
        reference_exists: Callable[[str], bool],
        unresolved: list[str],
        get_definition: Callable[[str], Any] | None = None,
        composite_stack: tuple[str, ...] = (),
    ) -> DanceNode:
        if (
            isinstance(value, list)
            and len(value) == 2
            and value[0] in ("s", "p")
            and isinstance(value[1], list)
        ):
            return GroupNode(
                id=cls._new_id(),
                kind="series" if value[0] == "s" else "parallel",
                children=tuple(
                    cls._parse_node(
                        child,
                        reference_exists,
                        unresolved,
                        get_definition,
                        composite_stack,
                    )
                    for child in value[1]
                ),
            )

        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Legacy FigureList node must be a group or anchored figure")
        anchor, target = value
        if (
            not isinstance(anchor, list)
            or len(anchor) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, Real)
                for item in anchor
            )
        ):
            raise ValueError("Legacy figure anchor must contain exactly two real numbers")

        if isinstance(target, str):
            figure_ref, addons = target, []
        elif (
            isinstance(target, list)
            and len(target) == 2
            and isinstance(target[0], str)
            and isinstance(target[1], list)
            and all(isinstance(addon, str) for addon in target[1])
        ):
            figure_ref, addons = target[0], target[1]
        else:
            raise ValueError("Legacy figure target must be a reference or [reference, addons]")
        if not figure_ref:
            raise ValueError("Legacy figure reference must not be empty")
        exists = reference_exists(figure_ref)
        if not exists:
            unresolved.append(figure_ref)
        elif get_definition is not None:
            definition = get_definition(figure_ref)
            if definition is not None and not isinstance(definition, dict):
                raise ValueError(f"Figure definition for {figure_ref!r} must be an object")
            if isinstance(definition, dict) and definition.get("Version") == 3:
                if figure_ref in composite_stack:
                    cycle = " -> ".join(composite_stack + (figure_ref,))
                    raise ValueError(f"Recursive composite figure reference: {cycle}")
                if "FigureList" not in definition:
                    raise ValueError(
                        f"Composite figure definition {figure_ref!r} has no FigureList"
                    )
                children = cls._parse_node(
                    definition["FigureList"],
                    reference_exists,
                    unresolved,
                    get_definition,
                    composite_stack + (figure_ref,),
                )
                if not isinstance(children, GroupNode):
                    raise ValueError(
                        f"Composite figure definition {figure_ref!r} must have a group root"
                    )
                return CompositeOccurrence(
                    id=cls._new_id(),
                    figure_ref=figure_ref,
                    anchor=(anchor[0], anchor[1]),
                    addons=tuple(addons),
                    root=children,
                )
        return FigureOccurrence(
            id=cls._new_id(),
            figure_ref=figure_ref,
            anchor=(anchor[0], anchor[1]),
            addons=tuple(addons),
        )

    @staticmethod
    def _new_id() -> str:
        return str(uuid4())
