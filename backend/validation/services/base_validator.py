"""
Base validator class.

Each source-type validator extends this and implements validate_row().

The ValidationResult dataclass is the contract between validators and
the ingestion pipeline — the pipeline doesn't need to know which
validator it's calling, just that it gets back a list of issues
and a severity summary.

Design note: we don't raise exceptions for validation failures.
A bad row is a valid business outcome (it becomes SUSPICIOUS, not a 500 error).
Exceptions are reserved for actual programming errors.
"""
from dataclasses import dataclass, field
from typing import Optional
from .issue_codes import IssueCode


@dataclass
class Issue:
    """A single validation problem found in a row."""
    code: str
    severity: str        # 'error' or 'warning'
    field_name: str
    message: str


@dataclass
class ValidationResult:
    """
    Result of validating a single raw record row.

    has_errors: True if any issue has severity='error'
                → row will be marked SUSPICIOUS
    issues: list of all found problems
    """
    issues: list = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def add_error(self, code: str, field_name: str, message: str):
        self.issues.append(Issue(code=code, severity="error",
                                 field_name=field_name, message=message))

    def add_warning(self, code: str, field_name: str, message: str):
        self.issues.append(Issue(code=code, severity="warning",
                                 field_name=field_name, message=message))


class BaseValidator:
    """
    Abstract base for all source-type validators.
    Subclasses must implement validate_row().
    """

    def validate_row(self, row: dict) -> ValidationResult:
        raise NotImplementedError("Subclasses must implement validate_row()")

    # --- Shared helper methods ---

    def _check_required(self, row: dict, fields: list, result: ValidationResult):
        """Flag any missing required field as an error."""
        for f in fields:
            value = row.get(f)
            if value is None or str(value).strip() == "":
                result.add_error(
                    code=IssueCode.MISSING_REQUIRED_FIELD,
                    field_name=f,
                    message=f"Required field '{f}' is missing or empty."
                )

    def _check_non_negative(self, row: dict, field: str, result: ValidationResult):
        """Flag negative numeric values as errors."""
        val = row.get(field)
        if val is None or str(val).strip() == "":
            return  # Handled by _check_required
        try:
            numeric = float(str(val).replace(",", "").strip())
            if numeric < 0:
                result.add_error(
                    code=IssueCode.NEGATIVE_VALUE,
                    field_name=field,
                    message=f"Field '{field}' has negative value: {val}"
                )
            elif numeric == 0:
                result.add_warning(
                    code=IssueCode.ZERO_VALUE,
                    field_name=field,
                    message=f"Field '{field}' is zero — unusual for activity data."
                )
        except (ValueError, TypeError):
            result.add_error(
                code=IssueCode.NEGATIVE_VALUE,  # reusing code; field is non-numeric
                field_name=field,
                message=f"Field '{field}' is not a valid number: '{val}'"
            )
