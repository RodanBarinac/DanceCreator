"""Shared parsing helpers for engine-recognized duration addon names."""

import re

_DURATION_ADDON = re.compile(r"^B([1-9][0-9]*)$")
_MALFORMED_DURATION_ADDON = re.compile(r"^B[0-9]+$")


def duration_addon_bars(name: str) -> int | None:
    """Return the bar count for a valid B<n> addon name, otherwise None."""
    match = _DURATION_ADDON.fullmatch(name)
    return int(match.group(1)) if match else None


def is_malformed_duration_addon(name: str) -> bool:
    """Recognize numeric B names that violate positive canonical B<n> syntax."""
    return bool(_MALFORMED_DURATION_ADDON.fullmatch(name)) and duration_addon_bars(name) is None
