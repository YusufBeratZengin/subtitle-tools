"""Subtitle linting and auto-fixing module."""

from subtitle_tools.lint.fixer import auto_fix_tags, fix_document
from subtitle_tools.lint.linter import check_unbalanced_tags, lint_document
from subtitle_tools.lint.rules import LintConfig, LintIssue, Severity

__all__ = [
    "LintConfig",
    "LintIssue",
    "Severity",
    "auto_fix_tags",
    "check_unbalanced_tags",
    "fix_document",
    "lint_document",
]
