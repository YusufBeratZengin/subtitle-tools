"""SubRip (.srt) parser and writer implementation."""

from __future__ import annotations

import re

from subtitle_tools.parsers.base import BaseSubtitleParser, BaseSubtitleWriter
from subtitle_tools.time import format_srt_time, parse_time
from subtitle_tools.types import Cue, SubtitleDocument

# Pattern for SubRip timestamp line: "00:01:20,000 --> 00:01:23,456"
_RE_SRT_TIMING = re.compile(
    r"(?P<start>(?:\d{1,2}:)?(?:\d{1,2}:)?\d{1,2}[,.]\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?(?:\d{1,2}:)?\d{1,2}[,.]\d{1,3})"
)


class SrtParser(BaseSubtitleParser):
    """Lenient parser for SubRip (.srt) subtitle files."""

    def parse(self, text: str) -> SubtitleDocument:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")

        cues: list[Cue] = []
        pending_index: int | None = None
        current_cue: Cue | None = None
        current_text_lines: list[str] = []

        i = 0
        n = len(lines)
        while i < n:
            raw_line = lines[i]
            line = raw_line.strip()

            timing_match = _RE_SRT_TIMING.search(line)
            if timing_match:
                # If we had a cue in progress, finalize it
                if current_cue is not None:
                    current_cue.text = "\n".join(current_text_lines).strip()
                    cues.append(current_cue)
                    current_cue = None
                    current_text_lines = []

                # Parse start and end times
                start_str = timing_match.group("start")
                end_str = timing_match.group("end")
                try:
                    start_ms = parse_time(start_str)
                    end_ms = parse_time(end_str)
                except ValueError:
                    # Skip malformed timing line
                    i += 1
                    continue

                idx = pending_index if pending_index is not None else len(cues) + 1
                current_cue = Cue(start=start_ms, end=end_ms, text="", index=idx)
                pending_index = None
                i += 1
                continue

            if current_cue is None:
                # Outside of a cue, check if this line is an integer index
                if line.isdigit():
                    pending_index = int(line)
                i += 1
                continue

            # We are inside a cue
            # If line is empty, check if subsequent line is a timing line or cue index
            if not line:
                # Look ahead to see if next non-empty line is a timing line or index
                next_idx = i + 1
                while next_idx < n and not lines[next_idx].strip():
                    next_idx += 1

                if next_idx < n:
                    next_line = lines[next_idx].strip()
                    if _RE_SRT_TIMING.search(next_line) or next_line.isdigit():
                        # End of current cue
                        current_cue.text = "\n".join(current_text_lines).strip()
                        cues.append(current_cue)
                        current_cue = None
                        current_text_lines = []
                        i = next_idx
                        continue
                else:
                    # End of file reached
                    current_cue.text = "\n".join(current_text_lines).strip()
                    cues.append(current_cue)
                    current_cue = None
                    current_text_lines = []
                    break

            # Collect line into current cue
            current_text_lines.append(raw_line)
            i += 1

        # Finalize any remaining cue
        if current_cue is not None:
            current_cue.text = "\n".join(current_text_lines).strip()
            cues.append(current_cue)

        return SubtitleDocument(format="srt", cues=cues)


class SrtWriter(BaseSubtitleWriter):
    """Standard writer for SubRip (.srt) subtitle files."""

    def write(self, doc: SubtitleDocument) -> str:
        blocks: list[str] = []
        for i, cue in enumerate(doc.cues, 1):
            idx = cue.index if cue.index is not None else i
            start_str = format_srt_time(cue.start)
            end_str = format_srt_time(cue.end)
            text = cue.text.rstrip()
            blocks.append(f"{idx}\n{start_str} --> {end_str}\n{text}")

        if not blocks:
            return ""
        return "\n\n".join(blocks) + "\n"
