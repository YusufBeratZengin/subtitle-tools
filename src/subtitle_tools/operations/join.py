"""Joining and concatenating subtitle documents."""

from __future__ import annotations

from subtitle_tools.time import parse_time
from subtitle_tools.types import Cue, SubtitleDocument


def join(
    docs: list[SubtitleDocument],
    gap_ms: int | str = 0,
    shift_sequential: bool = True,
) -> SubtitleDocument:
    """Concatenate multiple subtitle documents into a single document.

    Args:
        docs: List of SubtitleDocument instances to join in order.
        gap_ms: Optional gap duration in milliseconds between concatenated files.
        shift_sequential: If True, each subsequent file's cues are shifted after
            the end time of the preceding file plus the gap.

    Returns:
        A unified SubtitleDocument.
    """
    if not docs:
        raise ValueError("Cannot join an empty list of documents")

    gap = parse_time(str(gap_ms)) if isinstance(gap_ms, str) else gap_ms
    primary_doc = docs[0].clone()

    combined_cues: list[Cue] = []
    current_offset = 0

    for i, doc in enumerate(docs):
        if i > 0 and shift_sequential:
            # Shift cues of this doc by current_offset
            for cue in doc.cues:
                shifted = cue.clone()
                shifted.start += current_offset
                shifted.end += current_offset
                combined_cues.append(shifted)
        else:
            for cue in doc.cues:
                combined_cues.append(cue.clone())

        if doc.cues:
            doc_end = max(c.end for c in doc.cues)
            if shift_sequential:
                current_offset += doc_end + gap

    # Sort combined cues by start time
    combined_cues.sort(key=lambda c: (c.start, c.end))

    # Renumber sequentially
    for idx, cue in enumerate(combined_cues, 1):
        cue.index = idx

    primary_doc.cues = combined_cues
    return primary_doc
