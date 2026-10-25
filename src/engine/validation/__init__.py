"""Domain-level structured validation."""

from .errors import ValidationIssue, ValidationReport
from .validator import validate_document

__all__ = ["ValidationIssue", "ValidationReport", "validate_document"]
