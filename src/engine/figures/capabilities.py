from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .addon_utils import (
    duration_addon_bars,
    is_addon_array_noop,
    is_malformed_duration_addon,
    validate_addon_array_nulls,
    validate_end_facing_values,
)


class AddonValidationError(ValueError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        figure_ref: str,
        addons: tuple[str, ...],
        path: str,
        occurrence_id: str | None,
        dancers: tuple[str, ...] = (),
    ) -> None:
        self.code = code
        self.message = message
        self.figure_ref = figure_ref
        self.addons = addons
        self.path = path
        self.occurrence_id = occurrence_id
        self.dancers = tuple(dancers)
        self.field = "addons"
        super().__init__(message)


@dataclass(frozen=True)
class FigureDefinition:
    figure_ref: str
    name: str
    description: str
    version: int
    bars: int
    formation: str | None
    valid_addons: tuple[dict[str, Any], ...]
    capability_version: int
    supports_preview: bool
    allowed_addon_combinations: tuple[frozenset[str], ...] | None
    dancer_count: int


@dataclass(frozen=True)
class FigureCapabilities:
    figure_ref: str
    bars: int
    formation: str | None
    valid_addons: tuple[dict[str, Any], ...]
    supports_preview: bool
    capability_version: int
    duration_addon_pattern: str = "B<n>"


class FigureRepository:
    """Reads figure definitions and their engine-owned capability metadata."""

    def __init__(
        self,
        figure_directory: str | Path | None = None,
        dance_directory: str | Path | None = None,
    ) -> None:
        self.figure_directory = Path(
            figure_directory or Path.cwd() / "data" / "Figures"
        ).resolve()
        self.dance_directory = Path(
            dance_directory or Path.cwd() / "data" / "Dances"
        ).resolve()

    def get_definition(self, figure_ref: str) -> FigureDefinition:
        path = self._definition_path(figure_ref)
        with path.open("r", encoding="utf-8-sig") as source:
            data = json.load(source)
        if not isinstance(data, dict):
            raise ValueError(f"Figure definition must be an object: {figure_ref}")

        self._reject_legacy_faceing(data, figure_ref)

        version = data.get("Version")
        if isinstance(version, bool) or version != 2:
            raise ValueError(f"Unsupported simple figure definition version: {version!r}")
        name = data.get("Name", figure_ref)
        description = data.get("Desc", "")
        bars = data.get("Bars")
        formation = data.get("Formation")
        if not isinstance(name, str) or not name:
            raise ValueError("Figure Name must be a non-empty string")
        if not isinstance(description, str):
            raise ValueError("Figure Desc must be a string")
        if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1:
            raise ValueError("Figure Bars must be a positive integer")
        if formation is not None and not isinstance(formation, str):
            raise ValueError("Figure Formation must be a string or null")

        capability_version = data.get("CapabilityVersion", 1)
        if (
            isinstance(capability_version, bool)
            or not isinstance(capability_version, int)
            or capability_version < 1
        ):
            raise ValueError("CapabilityVersion must be a positive integer")
        valid_addons = self._normalize_addons(data.get("Addons", {}))
        allowed_combinations = self._parse_combination_validator(
            data.get("AddonCombinationValidator"),
            {addon["name"] for addon in valid_addons},
        )

        return FigureDefinition(
            figure_ref=figure_ref,
            name=name,
            description=description,
            version=version,
            bars=bars,
            formation=formation,
            valid_addons=valid_addons,
            capability_version=capability_version,
            supports_preview=True,
            allowed_addon_combinations=allowed_combinations,
            dancer_count=(len(data.get("StartPos", [])) if isinstance(data.get("StartPos", []), list) else 0),
        )

    def get_legacy_definition(self, figure_ref: str) -> dict[str, Any]:
        path = self._legacy_definition_path(figure_ref)
        with path.open("r", encoding="utf-8-sig") as source:
            definition = json.load(source)
        if not isinstance(definition, dict):
            raise ValueError(f"Figure definition must be an object: {figure_ref}")
        self._reject_legacy_faceing(definition, figure_ref)
        if definition.get("Version") not in (2, 3):
            raise ValueError(
                f"Unsupported legacy figure definition version: "
                f"{definition.get('Version')!r}"
            )
        return definition

    @staticmethod
    def _reject_legacy_faceing(definition: Mapping[str, Any], figure_ref: str) -> None:
        if "Faceing" in definition:
            raise ValueError(
                f"Unsupported legacy figure key 'Faceing' in {figure_ref!r}; use 'EndFacing'."
            )
        addons = definition.get("Addons")
        if isinstance(addons, Mapping):
            for addon_name, addon in addons.items():
                if isinstance(addon, Mapping) and "Faceing" in addon:
                    raise ValueError(
                        f"Unsupported legacy addon key 'Faceing' in addon {addon_name!r} "
                        f"of {figure_ref!r}; use 'EndFacing'."
                    )

    def figure_exists(self, figure_ref: str) -> bool:
        try:
            self._legacy_definition_path(figure_ref)
        except FileNotFoundError:
            return False
        return True

    def get_capabilities(self, figure_ref: str) -> FigureCapabilities:
        definition = self.get_definition(figure_ref)
        return FigureCapabilities(
            figure_ref=definition.figure_ref,
            bars=definition.bars,
            formation=definition.formation,
            valid_addons=tuple(deepcopy(definition.valid_addons)),
            supports_preview=definition.supports_preview,
            capability_version=definition.capability_version,
        )

    def validate_addons(
        self,
        figure_ref: str,
        addons: list[str] | tuple[str, ...],
        path: str,
        occurrence_id: str | None = None,
    ) -> None:
        definition = self.get_definition(figure_ref)
        all_dancers = tuple(
            f"start position {index + 1}"
            for index in range(definition.dancer_count)
        )
        if not isinstance(addons, (list, tuple)) or any(
            not isinstance(addon, str) for addon in addons
        ):
            self._raise_addon_error(
                code="invalid_addon_selection",
                message="Addon selection must be an array of strings.",
                figure_ref=figure_ref,
                addons=(),
                path=f"{path}.addons",
                occurrence_id=occurrence_id,
                dancers=all_dancers,
            )
        selected = tuple(addons)
        valid_names = {addon["name"] for addon in definition.valid_addons}
        duration_names = [name for name in selected if duration_addon_bars(name) is not None]
        if len(duration_names) > 1:
            self._raise_addon_error(
                code="addon_conflict",
                message=(f"Conflicting duration addons {duration_names[0]!r} and "
                         f"{duration_names[1]!r} both modify Bars."),
                figure_ref=figure_ref,
                addons=selected,
                path=f"{path}.addons",
                occurrence_id=occurrence_id,
                dancers=all_dancers,
            )
        for index, addon in enumerate(selected):
            if addon not in valid_names and duration_addon_bars(addon) is None:
                message = (
                    f"Invalid duration addon {addon!r}; use B<n> with a positive integer and no leading zero."
                    if is_malformed_duration_addon(addon)
                    else f"Addon {addon!r} is not supported by figure {figure_ref!r}."
                )
                self._raise_addon_error(
                    code="invalid_addon_selection" if is_malformed_duration_addon(addon) else "unsupported_addon",
                    message=message,
                    figure_ref=figure_ref,
                    addons=selected,
                    path=f"{path}.addons[{index}]",
                    occurrence_id=occurrence_id,
                    dancers=all_dancers,
                )
            if addon in selected[:index]:
                self._raise_addon_error(
                    code="invalid_addon_selection",
                    message=f"Addon {addon!r} is selected more than once.",
                    figure_ref=figure_ref,
                    addons=selected,
                    path=f"{path}.addons[{index}]",
                    occurrence_id=occurrence_id,
                    dancers=all_dancers,
                )

        self._validate_selected_conflicts(
            selected, definition.valid_addons, figure_ref, path, occurrence_id, all_dancers
        )
        combinations = definition.allowed_addon_combinations
        combination_selection = frozenset(
            addon for addon in selected if duration_addon_bars(addon) is None
        )
        if combinations is not None and combination_selection not in combinations:
            self._raise_addon_error(
                code="invalid_addon_combination",
                message=f"Addon combination is not supported by figure {figure_ref!r}.",
                figure_ref=figure_ref,
                addons=selected,
                path=f"{path}.addons",
                occurrence_id=occurrence_id,
                dancers=all_dancers,
            )

    @staticmethod
    def _validate_selected_conflicts(
        selected, addon_definitions, figure_ref, path, occurrence_id, all_dancers=()
    ):
        writes = {}
        definition_map = {addon["name"]: addon["parameters"] for addon in addon_definitions}
        fields = ("Bars", "StartPos", "EndPos", "EndFacing", "Partner")
        duration_names = [name for name in selected if duration_addon_bars(name) is not None]
        if duration_names:
            for name in selected:
                if name not in duration_names and "Bars" in definition_map.get(name, {}):
                    FigureRepository._raise_addon_error(
                        code="addon_conflict",
                        message=f"Conflicting addons {name!r} and {duration_names[0]!r} modify Bars.",
                        figure_ref=figure_ref, addons=tuple(selected),
                        path=f"{path}.addons", occurrence_id=occurrence_id,
                        dancers=all_dancers,
                    )
        for name in selected:
            data = definition_map.get(name, {})
            for field in fields:
                if field not in data:
                    continue
                values = data[field]
                entries = [(None, values)] if field == "Bars" else (
                    [(index, value) for index, value in enumerate(values)
                     if not is_addon_array_noop(field, value)]
                    if isinstance(values, (list, tuple)) else []
                )
                for index, value in entries:
                    key = (field, index)
                    if key in writes:
                        other, other_value = writes[key]
                        dancer = "all dancers" if index is None else f"dancer {index + 1}"
                        FigureRepository._raise_addon_error(
                            code="addon_conflict",
                            message=(f"Conflicting addons {other!r} and {name!r} modify {field} "
                                     f"for {dancer}: {other_value!r} vs {value!r}."),
                            figure_ref=figure_ref, addons=tuple(selected),
                            path=f"{path}.addons", occurrence_id=occurrence_id,
                            dancers=(all_dancers[index] if index < len(all_dancers) else f"start position {index + 1}",),
                        )
                    writes[key] = (name, value)
            descriptions = data.get("CriptDesc", [])
            replacements = data.get("CriptReplace", [])
            if isinstance(descriptions, (list, tuple)) and isinstance(replacements, (list, tuple)):
                for index, (replacement, target) in enumerate(zip(descriptions, replacements)):
                    if not replacement or not target:
                        continue
                    key = ("CriptDesc", index)
                    value = {"replace": target, "with": replacement}
                    if key in writes:
                        other, other_value = writes[key]
                        FigureRepository._raise_addon_error(
                            code="addon_conflict",
                            message=(f"Conflicting addons {other!r} and {name!r} modify CriptDesc "
                                     f"for dancer {index + 1}: {other_value!r} vs {value!r}."),
                            figure_ref=figure_ref, addons=tuple(selected),
                            path=f"{path}.addons", occurrence_id=occurrence_id,
                            dancers=(all_dancers[index] if index < len(all_dancers) else f"start position {index + 1}",),
                        )
                    writes[key] = (name, value)
        if duration_names:
            key = ("Bars", None)
            if key in writes:
                other, other_value = writes[key]
                FigureRepository._raise_addon_error(
                    code="addon_conflict",
                    message=(f"Conflicting addons {other!r} and {duration_names[0]!r} modify "
                             f"Bars for all dancers: {other_value!r} vs "
                             f"{duration_addon_bars(duration_names[0])!r}."),
                    figure_ref=figure_ref, addons=tuple(selected),
                    path=f"{path}.addons", occurrence_id=occurrence_id, dancers=all_dancers,
                )

    def _definition_path(self, figure_ref: str) -> Path:
        return self._path_under_root(figure_ref, self.figure_directory)

    def _legacy_definition_path(self, figure_ref: str) -> Path:
        self._validate_figure_ref(figure_ref)
        seen_paths: set[Path] = set()
        for root in (self.figure_directory, self.dance_directory):
            direct = root / f"{figure_ref}.json"
            if direct.exists():
                return self._path_under_root(figure_ref, root)
            if not root.is_dir():
                continue
            for candidate in sorted(root.rglob("*.json")):
                if candidate.stem.casefold() != figure_ref.casefold():
                    continue
                resolved = candidate.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                try:
                    resolved.relative_to(root)
                except ValueError:
                    raise ValueError("Invalid figure reference")
                if resolved.is_file():
                    return resolved
        raise FileNotFoundError(f"Figure definition not found: {figure_ref}")

    @staticmethod
    def _validate_figure_ref(figure_ref: str) -> None:
        if (
            not isinstance(figure_ref, str)
            or not figure_ref
            or figure_ref.strip() != figure_ref
            or figure_ref in (".", "..")
            or "/" in figure_ref
            or "\\" in figure_ref
        ):
            raise ValueError("Invalid figure reference")

    @classmethod
    def _path_under_root(cls, figure_ref: str, root: Path) -> Path:
        cls._validate_figure_ref(figure_ref)
        path = (root / f"{figure_ref}.json").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise ValueError("Invalid figure reference")
        if not path.is_file():
            raise FileNotFoundError(f"Figure definition not found: {figure_ref}")
        return path

    @staticmethod
    def _normalize_addons(addons: Any) -> tuple[dict[str, Any], ...]:
        normalized: list[dict[str, Any]] = []
        if isinstance(addons, Mapping):
            entries = addons.items()
        elif isinstance(addons, list):
            entries = []
            for item in addons:
                if isinstance(item, str):
                    entries.append((item, {}))
                elif isinstance(item, dict):
                    name = item.get("Name", item.get("name"))
                    if not isinstance(name, str):
                        raise ValueError("Addon entries must define a name")
                    entries.append((name, item))
                else:
                    raise ValueError("Addons must be a name map or an array of addon definitions")
        else:
            raise ValueError("Addons must be a name map or an array of addon definitions")

        for name, definition in entries:
            if not isinstance(name, str) or not name:
                raise ValueError("Addon names must be non-empty strings")
            if duration_addon_bars(name) is not None:
                raise ValueError(
                    f"Addon {name!r} uses the reserved B<n> duration addon name."
                )
            if not isinstance(definition, Mapping):
                raise ValueError(f"Addon definition for {name!r} must be an object")
            validate_addon_array_nulls(name, definition)
            if "EndFacing" in definition:
                validate_end_facing_values(
                    definition["EndFacing"],
                    owner=f"Addon {name!r} EndFacing",
                    allow_null=True,
                )
            description = definition.get("Desc", definition.get("description", ""))
            if not isinstance(description, str):
                raise ValueError(f"Addon description for {name!r} must be a string")
            parameters = {
                key: deepcopy(value)
                for key, value in definition.items()
                if key not in ("Name", "name", "Desc", "description", "Version")
            }
            normalized.append(
                {"name": name, "description": description, "parameters": parameters}
            )
        return tuple(normalized)

    @staticmethod
    def _parse_combination_validator(
        validator: Any,
        valid_addon_names: set[str],
    ) -> tuple[frozenset[str], ...] | None:
        if validator is None:
            return None
        if not isinstance(validator, dict) or set(validator) != {"allowedCombinations"}:
            raise ValueError(
                "AddonCombinationValidator must contain only allowedCombinations"
            )
        combinations = validator["allowedCombinations"]
        if not isinstance(combinations, list):
            raise ValueError("allowedCombinations must be an array")

        normalized = []
        for combination in combinations:
            if not isinstance(combination, list) or any(
                not isinstance(addon, str) for addon in combination
            ):
                raise ValueError("Each allowed addon combination must be an array of strings")
            unknown = set(combination) - valid_addon_names
            if unknown:
                raise ValueError(
                    f"Addon combination validator references unsupported addons: {sorted(unknown)}"
                )
            normalized.append(frozenset(combination))
        return tuple(normalized)

    @staticmethod
    def _raise_addon_error(
        *,
        code: str,
        message: str,
        figure_ref: str,
        addons: tuple[str, ...],
        path: str,
        occurrence_id: str | None,
        dancers: tuple[str, ...] = (),
    ) -> None:
        raise AddonValidationError(
            code=code,
            message=message,
            figure_ref=figure_ref,
            addons=addons,
            path=path,
            occurrence_id=occurrence_id,
            dancers=dancers,
        )
