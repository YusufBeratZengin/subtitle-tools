"""Tag stripping and text normalization operations for subtitles."""

from __future__ import annotations

import html
import re

from subtitle_tools.types import SubtitleDocument

# Regex to match ASS style override tags: {\...}
_RE_ASS_TAG = re.compile(r"\{[^}]*\}")

# Regex to match HTML / WebVTT tags: <...>
_RE_HTML_VTT_TAG = re.compile(r"<[^>]+>")


def strip_formatting_tags(text: str) -> str:
    """Remove HTML, WebVTT, and ASS formatting tags from text.

    Examples:
        - "<i>Hello</i> <b>world</b>" -> "Hello world"
        - "<v Speaker 1>Welcome</v>" -> "Welcome"
        - "{\\pos(192,100)\\b1}Sample{\\b0}" -> "Sample"
        - "Line 1\\NLine 2" -> "Line 1\\nLine 2"
    """
    if not text:
        return ""

    # Replace ASS line breaks and hard spaces
    s = text.replace(r"\N", "\n").replace(r"\n", "\n").replace(r"\h", " ")

    # Remove ASS override tags {\...}
    s = _RE_ASS_TAG.sub("", s)

    # Remove HTML / WebVTT tags <...>
    s = _RE_HTML_VTT_TAG.sub("", s)

    # Unescape HTML entities (&amp; -> &, &lt; -> <, etc.)
    s = html.unescape(s)

    # Clean redundant whitespace on each line while preserving newlines
    lines = [line.strip() for line in s.split("\n")]
    # Strip empty leading/trailing lines
    cleaned = "\n".join(lines).strip()
    return cleaned


def strip_tags(doc: SubtitleDocument) -> SubtitleDocument:
    """Return a new SubtitleDocument with all formatting tags stripped from all cues."""
    new_doc = doc.clone()
    for cue in new_doc.cues:
        cue.text = strip_formatting_tags(cue.text)
    return new_doc
