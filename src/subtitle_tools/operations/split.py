"""Splitting subtitle documents by duration intervals."""

from __future__ import annotations

from subtitle_tools.time import parse_time
from subtitle_tools.types import Cue, SubtitleDocument


def split(
    doc: SubtitleDocument,
    duration_ms: int | str,
    relative_times: bool = True,
) -> list[SubtitleDocument]:
    """Split a subtitle document into multiple parts based on chunk duration.

    Args:
        doc: SubtitleDocument to split.
        duration_ms: Duration of each chunk (integer ms or time string like '20m', '00:20:00.000').
        relative_times: If True, each chunk's timestamps are offset to start at 0.

    Returns:
        List of SubtitleDocument instances for each chunk.
    """
    chunk_dur = parse_time(str(duration_ms)) if isinstance(duration_ms, str) else duration_ms
    if chunk_dur <= 0:
        raise ValueError("Chunk duration must be positive")

    if not doc.cues:
        return [doc.clone()]

    total_dur = doc.total_duration
    num_chunks = max(1, (total_dur + chunk_dur - 1) // chunk_dur)

    chunks: list[SubtitleDocument] = []
    sorted_cues = sorted(doc.cues, key=lambda c: (c.start, c.end))

    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * chunk_dur
        chunk_end = (chunk_idx + 1) * chunk_dur

        chunk_cues: list[Cue] = []
        for cue in sorted_cues:
            # Assign cue to chunk if its start time falls within chunk range
            if chunk_start <= cue.start < chunk_end:
                new_cue = cue.clone()
                if relative_times:
                    new_cue.start = max(0, new_cue.start - chunk_start)
                    new_cue.end = max(0, new_cue.end - chunk_start)
                chunk_cues.append(new_cue)

        # Renumber cues in this chunk
        for i, c in enumerate(chunk_cues, 1):
            c.index = i

        chunk_doc = doc.clone()
        chunk_doc.cues = chunk_cues
        chunks.append(chunk_doc)

    return chunks
