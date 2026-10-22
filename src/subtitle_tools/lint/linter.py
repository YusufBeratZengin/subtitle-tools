"""Subtitle linter implementation."""

from __future__ import annotations

import re

from subtitle_tools.lint.rules import LintConfig, LintIssue
from subtitle_tools.operations.tags import strip_formatting_tags
from subtitle_tools.types import SubtitleDocument

# Tags to validate for balance
_RE_HTML_TAG = re.compile(r"<\s*(/)?\s*([a-zA-Z0-9_\-\.]+)(?:\s+[^>]*)?>")
_VOID_TAGS = {"br", "hr", "img"}


def check_unbalanced_tags(text: str) -> tuple[bool, str]:
    """Check if text has unclosed or mismatched HTML/VTT or ASS tags.

    Returns:
        (is_unbalanced, description_of_issue)
    """
    # Check ASS curly brackets
    open_curly = text.count("{")
    close_curly = text.count("}")
    if open_curly != close_curly:
        return True, f"Mismatched curly braces for styling: {open_curly} '{{' vs {close_curly} '}}'"

    stack: list[str] = []
    for match in _RE_HTML_TAG.finditer(text):
        is_closing = bool(match.group(1))
        tag_name = match.group(2).lower()

        if tag_name in _VOID_TAGS:
            continue

        if is_closing:
            if not stack:
                return True, f"Unexpected closing tag </{tag_name}> without matching opening tag"
            top = stack[-1]
            if top != tag_name:
                return True, f"Mismatched closing tag </{tag_name}> (expected </{top}>)"
            stack.pop()
        else:
            stack.append(tag_name)

    if stack:
        unclosed = ", ".join(f"<{t}>" for t in stack)
        return True, f"Unclosed tag(s): {unclosed}"

    return False, ""


def lint_document(
    doc: SubtitleDocument,
    config: LintConfig | None = None,
    has_bom: bool = False,
    has_mixed_newlines: bool = False,
) -> list[LintIssue]:
    """Lint a SubtitleDocument against configured rules.

    Args:
        doc: SubtitleDocument to inspect.
        config: LintConfig options (or default if None).
        has_bom: Whether the file contains a UTF-8 BOM.
        has_mixed_newlines: Whether the file contains mixed CRLF/LF newlines.

    Returns:
        List of detected LintIssue instances.
    """
    cfg = config or LintConfig()
    issues: list[LintIssue] = []

    # File-level checks
    if cfg.is_rule_enabled("encoding-issue"):
        if has_bom:
            issues.append(
                LintIssue(
                    rule_id="encoding-issue",
                    message="File contains a UTF-8 Byte Order Mark (BOM)",
                    severity="warning",
                    fixable=True,
                    details={"type": "bom"},
                )
            )
        if has_mixed_newlines:
            issues.append(
                LintIssue(
                    rule_id="encoding-issue",
                    message="File contains mixed newline conventions (CRLF and LF)",
                    severity="warning",
                    fixable=True,
                    details={"type": "mixed_newlines"},
                )
            )

    prev_end: int | None = None

    for i, cue in enumerate(doc.cues, 1):
        cue_idx = cue.index if cue.index is not None else i
        st = cue.start
        en = cue.end
        dur = en - st

        # 1. Overlap rule
        if cfg.is_rule_enabled("overlap"):
            if prev_end is not None and st < prev_end:
                overlap_ms = prev_end - st
                can_fix = overlap_ms <= cfg.overlap_fix_threshold_ms
                issues.append(
                    LintIssue(
                        rule_id="overlap",
                        message=f"Cue overlaps previous cue by {overlap_ms}ms (starts at {st}ms, previous ended at {prev_end}ms)",
                        severity="error",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=can_fix,
                        details={"overlap_ms": overlap_ms},
                    )
                )

        # 2. Negative duration
        if cfg.is_rule_enabled("negative-duration"):
            if dur < 0:
                issues.append(
                    LintIssue(
                        rule_id="negative-duration",
                        message=f"Cue end time ({en}ms) is before start time ({st}ms)",
                        severity="error",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=True,
                    )
                )

        # 3. Zero duration
        if cfg.is_rule_enabled("zero-duration"):
            if dur == 0:
                issues.append(
                    LintIssue(
                        rule_id="zero-duration",
                        message=f"Cue duration is zero ({st}ms to {en}ms)",
                        severity="error",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=True,
                    )
                )

        # 4. Too short duration
        if cfg.is_rule_enabled("too-short-duration"):
            if 0 < dur < cfg.min_duration_ms:
                issues.append(
                    LintIssue(
                        rule_id="too-short-duration",
                        message=f"Cue duration ({dur}ms) is shorter than minimum ({cfg.min_duration_ms}ms)",
                        severity="warning",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=False,
                        details={"duration_ms": dur, "min_ms": cfg.min_duration_ms},
                    )
                )

        # 5. Too long duration
        if cfg.is_rule_enabled("too-long-duration"):
            if dur > cfg.max_duration_ms:
                issues.append(
                    LintIssue(
                        rule_id="too-long-duration",
                        message=f"Cue duration ({dur}ms) exceeds maximum ({cfg.max_duration_ms}ms)",
                        severity="warning",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=False,
                        details={"duration_ms": dur, "max_ms": cfg.max_duration_ms},
                    )
                )

        # 6. Empty cue
        visible_text = strip_formatting_tags(cue.text).strip()
        if cfg.is_rule_enabled("empty-cue"):
            if not visible_text:
                issues.append(
                    LintIssue(
                        rule_id="empty-cue",
                        message="Cue text is empty or contains only formatting/whitespace",
                        severity="error",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=True,
                    )
                )
                prev_end = en
                continue

        # 7. Unbalanced tags
        if cfg.is_rule_enabled("unbalanced-tags"):
            is_unbalanced, tag_desc = check_unbalanced_tags(cue.text)
            if is_unbalanced:
                issues.append(
                    LintIssue(
                        rule_id="unbalanced-tags",
                        message=f"Unbalanced tags: {tag_desc}",
                        severity="error",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=True,
                    )
                )

        # 8. Characters per second (CPS)
        if cfg.is_rule_enabled("cps-limit") and dur > 0:
            char_count = len(visible_text)
            cps = char_count / (dur / 1000.0)
            if cps > cfg.max_cps:
                issues.append(
                    LintIssue(
                        rule_id="cps-limit",
                        message=f"Reading speed {cps:.1f} cps exceeds limit ({cfg.max_cps:.1f} cps)",
                        severity="warning",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=False,
                        details={"cps": round(cps, 1), "limit": cfg.max_cps},
                    )
                )

        # 9. Line length
        if cfg.is_rule_enabled("line-length"):
            lines = visible_text.split("\n")
            for line_no, line_content in enumerate(lines, 1):
                length = len(line_content)
                if length > cfg.max_line_length:
                    issues.append(
                        LintIssue(
                            rule_id="line-length",
                            message=f"Line {line_no} length ({length} chars) exceeds maximum ({cfg.max_line_length})",
                            severity="warning",
                            cue_index=cue_idx,
                            cue_start=st,
                            cue_end=en,
                            fixable=False,
                            details={"line": line_no, "length": length, "max": cfg.max_line_length},
                        )
                    )

        # 10. Line count
        if cfg.is_rule_enabled("line-count"):
            non_empty_lines = [ln for ln in visible_text.split("\n") if ln.strip()]
            num_lines = len(non_empty_lines)
            if num_lines > cfg.max_lines:
                issues.append(
                    LintIssue(
                        rule_id="line-count",
                        message=f"Cue has {num_lines} lines (maximum allowed is {cfg.max_lines})",
                        severity="warning",
                        cue_index=cue_idx,
                        cue_start=st,
                        cue_end=en,
                        fixable=False,
                        details={"line_count": num_lines, "max_lines": cfg.max_lines},
                    )
                )

        prev_end = en

    return issues
