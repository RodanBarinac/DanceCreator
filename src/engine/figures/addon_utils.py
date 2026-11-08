"""Shared parsing helpers for engine-recognized duration addon names."""

import math
import re

_DURATION_ADDON = re.compile(r"^B([1-9][0-9]*)$")
_MALFORMED_DURATION_ADDON = re.compile(r"^B[0-9]+$")
END_FACING_NOTATIONS = frozenset({"=", "I", "O", "U", "D", "OwnL", "OpL", "M"})
_ADDON_ARRAY_FIELDS = (
    "StartPos",
    "EndPos",
    "EndFacing",
    "Partner",
    "CriptDesc",
    "CriptReplace",
)


def _contains_null(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple)):
        return any(_contains_null(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_null(item) for item in value.values())
    return False


def duration_addon_bars(name: str) -> int | None:
    """Return the bar count for a valid B<n> addon name, otherwise None."""
    match = _DURATION_ADDON.fullmatch(name)
    return int(match.group(1)) if match else None


def is_malformed_duration_addon(name: str) -> bool:
    """Recognize numeric B names that violate positive canonical B<n> syntax."""
    return bool(_MALFORMED_DURATION_ADDON.fullmatch(name)) and duration_addon_bars(name) is None


def validate_addon_array_nulls(name: str, definition) -> None:
    """Allow null only as an explicit per-dancer EndFacing reset."""
    for field in _ADDON_ARRAY_FIELDS:
        if field not in definition:
            continue
        values = definition[field]
        if values is None:
            raise ValueError(
                f"Addon {name!r} field {field} must be an array; null is only valid "
                "as an entry in EndFacing."
            )
        if isinstance(values, (list, tuple)):
            for value in values:
                # A top-level null entry is the one supported reset operation.
                if field == "EndFacing" and value is None:
                    continue
                if _contains_null(value):
                    raise ValueError(
                        f"Addon {name!r} field {field} cannot contain null entries."
                    )


def validate_end_facing_values(values, *, owner="EndFacing", allow_null=False) -> None:
    """Validate target-coordinate, empty, and agreed symbolic facing entries."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{owner} must be an array of facing entries")
    for index, value in enumerate(values):
        if value is None and allow_null:
            continue
        if isinstance(value, str):
            if value not in END_FACING_NOTATIONS:
                raise ValueError(
                    f"Invalid {owner} entry at index {index}: unsupported facing notation {value!r}."
                )
            continue
        if value == []:
            continue
        if (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(
                not isinstance(component, bool)
                and isinstance(component, (int, float))
                and math.isfinite(component)
                for component in value
            )
        ):
            continue
        raise ValueError(
            f"Invalid {owner} entry at index {index}; expected an empty entry, "
            "a finite target coordinate pair, an agreed notation, or an allowed null reset."
        )


def is_addon_array_noop(field: str, value) -> bool:
    """Return whether an addon array entry leaves its base value unchanged."""
    return value == [] or value == "" or (value is None and field != "EndFacing")
