"""Time shifting operations for subtitles."""

from __future__ import annotations

from subtitle_tools.time import parse_offset, parse_time
from subtitle_tools.types import SubtitleDocument


def shift(
    doc: SubtitleDocument,
    by_ms: int | str | None = None,
    to_ms: int | str | None = None,
    drop_negative: bool = False,
) -> SubtitleDocument:
    """Shift all cue timings by an offset or by aligning the first cue.

    Args:
        doc: SubtitleDocument to shift.
        by_ms: Positive or negative offset (integer ms or string like '1500ms', '-2.5s').
        to_ms: Target timestamp for the first cue's start time (integer ms or time string).
        drop_negative: If True, cues that end at or before 0ms after shifting are dropped.

    Returns:
        A new SubtitleDocument with shifted timings.
    """
    new_doc = doc.clone()
    if not new_doc.cues:
        return new_doc

    delta: int = 0
    if to_ms is not None:
        target_start = parse_time(str(to_ms)) if isinstance(to_ms, str) else to_ms
        first_cue_start = new_doc.cues[0].start
        delta = target_start - first_cue_start
    elif by_ms is not None:
        delta = parse_offset(str(by_ms)) if isinstance(by_ms, str) else by_ms
    else:
        raise ValueError("Either 'by_ms' or 'to_ms' must be provided to shift.")

    shifted_cues = []
    for cue in new_doc.cues:
        new_start = cue.start + delta
        new_end = cue.end + delta

        if drop_negative and new_end <= 0:
            continue

        cue.start = max(0, new_start)
        cue.end = max(0, new_end)
        shifted_cues.append(cue)

    new_doc.cues = shifted_cues
    return new_doc
