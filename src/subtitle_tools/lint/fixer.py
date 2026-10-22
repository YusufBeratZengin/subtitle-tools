"""Auto-fixer implementation for safe subtitle lint rules."""

from __future__ import annotations

import re

from subtitle_tools.lint.rules import LintConfig
from subtitle_tools.operations.renumber import renumber
from subtitle_tools.operations.tags import strip_formatting_tags
from subtitle_tools.types import Cue, SubtitleDocument

_RE_TAG_TOKEN = re.compile(r"(<\s*(/)?\s*([a-zA-Z0-9_\-\.]+)(?:\s+[^>]*)?>)")
_VOID_TAGS = {"br", "hr", "img"}


def auto_fix_tags(text: str) -> str:
    """Auto-repair unbalanced HTML/VTT and ASS tags in text."""
    if not text:
        return ""

    # Fix ASS curly brackets
    fixed = text
    open_c = fixed.count("{")
    close_c = fixed.count("}")
    if open_c > close_c:
        fixed += "}" * (open_c - close_c)
    elif close_c > open_c:
        # Remove trailing/orphan closing curly braces
        excess = close_c - open_c
        parts = fixed.rsplit("}", excess)
        fixed = "".join(parts)

    # Process HTML / VTT tags
    tokens = _RE_TAG_TOKEN.split(fixed)
    # _RE_TAG_TOKEN.split with 3 capturing groups yields chunks:
    # chunk 0: text before
    # chunk 1: full match <...>
    # chunk 2: "/" if closing, else None
    # chunk 3: tag name
    # chunk 4: text after
    result_pieces: list[str] = []
    open_stack: list[str] = []

    pos = 0
    matches = list(_RE_TAG_TOKEN.finditer(fixed))
    if not matches:
        return fixed

    last_end = 0
    for match in matches:
        # Append text before tag
        result_pieces.append(fixed[last_end:match.start()])
        last_end = match.end()

        full_tag = match.group(1)
        is_closing = bool(match.group(2))
        tag_name = match.group(3).lower()

        if tag_name in _VOID_TAGS:
            result_pieces.append(full_tag)
            continue

        if is_closing:
            if tag_name in open_stack:
                # Close any tags opened after this tag
                while open_stack and open_stack[-1] != tag_name:
                    unclosed_tag = open_stack.pop()
                    result_pieces.append(f"</{unclosed_tag}>")
                if open_stack and open_stack[-1] == tag_name:
                    open_stack.pop()
                    result_pieces.append(full_tag)
            else:
                # Orphan closing tag, omit it
                pass
        else:
            open_stack.append(tag_name)
            result_pieces.append(full_tag)

    # Append remaining trailing text
    result_pieces.append(fixed[last_end:])

    # Close any unclosed tags
    while open_stack:
        tag_to_close = open_stack.pop()
        result_pieces.append(f"</{tag_to_close}>")

    return "".join(result_pieces)


def fix_document(
    doc: SubtitleDocument,
    config: LintConfig | None = None,
) -> tuple[SubtitleDocument, int]:
    """Apply safe auto-fixes to a SubtitleDocument.

    Fixes:
    - Removes empty cues.
    - Closes or strips unbalanced tags.
    - Resolves zero or negative durations.
    - Fixes overlaps within threshold.
    - Renumbers remaining cues.

    Returns:
        (fixed_doc, number_of_fixes_applied)
    """
    cfg = config or LintConfig()
    new_doc = doc.clone()
    fixes_count = 0

    # 1. Filter out empty cues
    retained_cues: list[Cue] = []
    for cue in new_doc.cues:
        visible = strip_formatting_tags(cue.text).strip()
        if not visible:
            fixes_count += 1
            continue

        # 2. Fix unbalanced tags
        if cfg.is_rule_enabled("unbalanced-tags"):
            fixed_text = auto_fix_tags(cue.text)
            if fixed_text != cue.text:
                cue.text = fixed_text
                fixes_count += 1

        # 3. Fix negative or zero duration
        dur = cue.end - cue.start
        if dur < 0 and cfg.is_rule_enabled("negative-duration"):
            # If start was mistakenly larger than end
            if cue.start - cue.end >= cfg.min_duration_ms:
                cue.start, cue.end = cue.end, cue.start
            else:
                cue.end = cue.start + cfg.min_duration_ms
            fixes_count += 1
        elif dur == 0 and cfg.is_rule_enabled("zero-duration"):
            cue.end = cue.start + cfg.min_duration_ms
            fixes_count += 1

        retained_cues.append(cue)

    # Sort cues chronologically
    retained_cues.sort(key=lambda c: (c.start, c.end))

    # 4. Fix overlaps
    if cfg.is_rule_enabled("overlap"):
        for i in range(1, len(retained_cues)):
            prev = retained_cues[i - 1]
            curr = retained_cues[i]
            if curr.start < prev.end:
                overlap_ms = prev.end - curr.start
                if overlap_ms <= cfg.overlap_fix_threshold_ms:
                    # Shorten previous cue end to current cue start
                    if curr.start > prev.start:
                        prev.end = curr.start
                        fixes_count += 1

    new_doc.cues = retained_cues
    # 5. Renumber
    new_doc = renumber(new_doc, start_index=1, sort_first=True)

    return new_doc, fixes_count
