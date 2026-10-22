"""Merging subtitle documents into dual-language stacked cues."""

from __future__ import annotations

from subtitle_tools.types import Cue, SubtitleDocument


def merge(
    doc1: SubtitleDocument,
    doc2: SubtitleDocument,
    separator: str = "\n",
    timing: str = "union",  # "union", "primary", or "secondary"
    keep_unmatched: bool = True,
) -> SubtitleDocument:
    """Merge two subtitle files (e.g., dual audio/language) into stacked cues.

    Args:
        doc1: Primary subtitle document (stacked first / top).
        doc2: Secondary subtitle document (stacked second / bottom).
        separator: String placed between primary and secondary text (default: newline).
        timing: Timing strategy for paired cues:
            - 'union': min(start1, start2) to max(end1, end2)
            - 'primary': start1 to end1
            - 'secondary': start2 to end2
        keep_unmatched: If True, cues in either document with no overlap are included.

    Returns:
        A new SubtitleDocument containing stacked cues sorted chronologically.
    """
    cues1 = sorted(doc1.cues, key=lambda c: (c.start, c.end))
    cues2 = sorted(doc2.cues, key=lambda c: (c.start, c.end))

    matched_cues2: set[int] = set()
    result_cues: list[Cue] = []

    for i, c1 in enumerate(cues1):
        # Find all cues in doc2 that overlap with c1
        overlapping = [
            (j, c2) for j, c2 in enumerate(cues2)
            if max(c1.start, c2.start) < min(c1.end, c2.end)
        ]

        if overlapping:
            # Mark doc2 cues as matched
            c2_texts: list[str] = []
            starts = [c1.start]
            ends = [c1.end]
            for j, c2 in overlapping:
                matched_cues2.add(j)
                c2_texts.append(c2.text.strip())
                starts.append(c2.start)
                ends.append(c2.end)

            stacked_text = f"{c1.text.strip()}{separator}{separator.join(c2_texts)}"

            if timing == "primary":
                st, en = c1.start, c1.end
            elif timing == "secondary":
                st = min(c2.start for _, c2 in overlapping)
                en = max(c2.end for _, c2 in overlapping)
            else:  # union
                st = min(starts)
                en = max(ends)

            result_cues.append(
                Cue(
                    start=st,
                    end=en,
                    text=stacked_text,
                    style=c1.style,
                    settings=c1.settings,
                )
            )
        else:
            if keep_unmatched:
                result_cues.append(c1.clone())

    # Add unmatched cues from doc2
    if keep_unmatched:
        for j, c2 in enumerate(cues2):
            if j not in matched_cues2:
                result_cues.append(c2.clone())

    # Sort results by start time
    result_cues.sort(key=lambda c: (c.start, c.end))

    # Renumber sequentially
    for idx, cue in enumerate(result_cues, 1):
        cue.index = idx

    new_doc = doc1.clone()
    new_doc.cues = result_cues
    return new_doc
