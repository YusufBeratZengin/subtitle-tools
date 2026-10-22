"""Format conversion operations for subtitle documents."""

from __future__ import annotations

from subtitle_tools.operations.tags import strip_formatting_tags
from subtitle_tools.parsers.ass import (
    DEFAULT_EVENTS_FORMAT,
    DEFAULT_STYLE_LINE,
    DEFAULT_STYLES_FORMAT,
)
from subtitle_tools.types import SubtitleDocument


def convert(
    doc: SubtitleDocument,
    target_format: str,
    strip_incompatible_tags: bool = True,
) -> SubtitleDocument:
    """Convert a SubtitleDocument to another target format (srt, vtt, ass).

    Args:
        doc: Source SubtitleDocument.
        target_format: Target format identifier ('srt', 'vtt', or 'ass').
        strip_incompatible_tags: If True, strips styling tags incompatible with target.

    Returns:
        A new SubtitleDocument formatted for the target format.
    """
    target = target_format.lower().lstrip(".")
    if target in ("ssa", "ass"):
        target = "ass"
    elif target in ("webvtt", "vtt"):
        target = "vtt"
    elif target == "srt":
        target = "srt"
    else:
        raise ValueError(f"Unsupported target format: '{target_format}'. Supported: srt, vtt, ass")

    new_doc = doc.clone()
    new_doc.format = target

    if target == "srt":
        for cue in new_doc.cues:
            cue.settings = None
            cue.identifier = None
            if strip_incompatible_tags and doc.format in ("ass", "ssa"):
                cue.text = strip_formatting_tags(cue.text)

    elif target == "vtt":
        if not new_doc.vtt_header or not new_doc.vtt_header.startswith("WEBVTT"):
            new_doc.vtt_header = "WEBVTT"
        for cue in new_doc.cues:
            if strip_incompatible_tags and doc.format in ("ass", "ssa"):
                cue.text = strip_formatting_tags(cue.text)

    elif target == "ass":
        if not new_doc.ass_script_info:
            new_doc.ass_script_info = [
                (";", " Converted by subtitle-tools"),
                ("Title", "Converted Subtitle"),
                ("ScriptType", "v4.00+"),
                ("WrapStyle", "0"),
                ("ScaledBorderAndShadow", "yes"),
            ]
        if not new_doc.ass_styles:
            new_doc.ass_styles = [DEFAULT_STYLES_FORMAT, DEFAULT_STYLE_LINE]
        if not new_doc.ass_events_format:
            new_doc.ass_events_format = [
                c.strip().lower()
                for c in DEFAULT_EVENTS_FORMAT.split(":", 1)[1].split(",")
            ]

    return new_doc
