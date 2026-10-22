"""Lint issue definitions and configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]


@dataclass
class LintIssue:
    """Represents a single issue found by the linter."""

    rule_id: str
    message: str
    severity: Severity = "warning"
    cue_index: int | None = None
    cue_start: int | None = None
    cue_end: int | None = None
    fixable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert issue to serializable dictionary."""
        d: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "fixable": self.fixable,
        }
        if self.cue_index is not None:
            d["cue_index"] = self.cue_index
        if self.cue_start is not None:
            d["cue_start"] = self.cue_start
        if self.cue_end is not None:
            d["cue_end"] = self.cue_end
        if self.details:
            d["details"] = self.details
        return d


@dataclass
class LintConfig:
    """Configuration options for subtitle linting rules."""

    max_cps: float = 17.0
    max_line_length: int = 42
    max_lines: int = 2
    min_duration_ms: int = 500
    max_duration_ms: int = 7000
    overlap_fix_threshold_ms: int = 1500
    disabled_rules: set[str] = field(default_factory=set)

    def is_rule_enabled(self, rule_id: str) -> bool:
        """Check whether a rule is enabled."""
        return rule_id not in self.disabled_rules
