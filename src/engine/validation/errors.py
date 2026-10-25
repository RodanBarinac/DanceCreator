"""Structured domain-validation results."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class ValidationIssue:
    """One actionable validation error or warning at a canonical tree location."""

    code: str
    severity: str
    path: str
    node_id: str | None
    occurrence_id: str | None
    field: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _freeze(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "nodeId": self.node_id,
            "occurrenceId": self.occurrence_id,
            "field": self.field,
            "message": self.message,
            "details": _thaw(self.details),
        }


@dataclass(frozen=True)
class ValidationReport:
    """A deterministic report; every error is blocking for execution."""

    errors: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def first_blocking(self) -> ValidationIssue | None:
        return self.errors[0] if self.errors else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "isValid": self.is_valid,
            "firstBlocking": (
                self.first_blocking.to_dict() if self.first_blocking else None
            ),
        }
