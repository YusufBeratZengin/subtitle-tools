"""Renumbering operations for subtitle cues."""

from __future__ import annotations

from subtitle_tools.types import SubtitleDocument


def renumber(
    doc: SubtitleDocument,
    start_index: int = 1,
    sort_first: bool = True,
) -> SubtitleDocument:
    """Renumber all cues in a SubtitleDocument sequentially.

    Args:
        doc: SubtitleDocument to renumber.
        start_index: Starting integer index (default: 1).
        sort_first: If True, cues are sorted by (start, end) time before renumbering.

    Returns:
        A new SubtitleDocument with sequential indices.
    """
    new_doc = doc.clone()
    if sort_first:
        new_doc.cues.sort(key=lambda c: (c.start, c.end))

    for idx, cue in enumerate(new_doc.cues, start_index):
        cue.index = idx

    return new_doc
