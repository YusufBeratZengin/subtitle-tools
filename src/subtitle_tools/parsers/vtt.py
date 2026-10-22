"""WebVTT (.vtt) parser and writer implementation."""

from __future__ import annotations

import re

from subtitle_tools.parsers.base import BaseSubtitleParser, BaseSubtitleWriter
from subtitle_tools.time import format_vtt_time, parse_time
from subtitle_tools.types import Cue, SubtitleDocument

# WebVTT timing line: leniently matching HH:MM:SS.mmm, MM:SS.mmm, or SS.mmm
_RE_VTT_TIMING = re.compile(
    r"^(?P<start>(?:(?:\d{1,2}:)?\d{1,2}:)?\d{1,2}[.,]\d{1,3})\s*-->\s*(?P<end>(?:(?:\d{1,2}:)?\d{1,2}:)?\d{1,2}[.,]\d{1,3})(?:\s+(?P<settings>.*))?$"
)


class VttParser(BaseSubtitleParser):
    """Parser for WebVTT (.vtt) subtitle files preserving cues, settings, and STYLE/NOTE blocks."""

    def parse(self, text: str) -> SubtitleDocument:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")

        vtt_header = "WEBVTT"
        vtt_styles: list[str] = []
        vtt_notes: list[str] = []
        vtt_regions: list[str] = []
        cues: list[Cue] = []

        i = 0
        n = len(lines)

        # Parse header
        while i < n and not lines[i].strip():
            i += 1

        if i < n and lines[i].startswith("WEBVTT"):
            vtt_header = lines[i].rstrip()
            i += 1

        # State machine to process blocks
        while i < n:
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Check for NOTE block
            if line.startswith("NOTE"):
                note_lines = [lines[i]]
                i += 1
                while i < n and lines[i].strip():
                    note_lines.append(lines[i])
                    i += 1
                vtt_notes.append("\n".join(note_lines))
                continue

            # Check for STYLE block
            if line.startswith("STYLE"):
                style_lines = [lines[i]]
                i += 1
                while i < n and lines[i].strip():
                    style_lines.append(lines[i])
                    i += 1
                vtt_styles.append("\n".join(style_lines))
                continue

            # Check for REGION block
            if line.startswith("REGION"):
                region_lines = [lines[i]]
                i += 1
                while i < n and lines[i].strip():
                    region_lines.append(lines[i])
                    i += 1
                vtt_regions.append("\n".join(region_lines))
                continue

            # Check for Cue: either identifier followed by timing, or timing directly
            identifier: str | None = None
            timing_match = _RE_VTT_TIMING.match(line)

            if not timing_match and i + 1 < n:
                # Potential identifier line. Check if next line is a timing line.
                next_timing_match = _RE_VTT_TIMING.match(lines[i + 1].strip())
                if next_timing_match:
                    identifier = line
                    i += 1
                    timing_match = next_timing_match

            if timing_match:
                start_str = timing_match.group("start")
                end_str = timing_match.group("end")
                settings = timing_match.group("settings")
                settings_str = settings.strip() if settings else None

                try:
                    start_ms = parse_time(start_str)
                    end_ms = parse_time(end_str)
                except ValueError:
                    i += 1
                    continue

                i += 1
                # Collect cue payload until blank line
                cue_lines: list[str] = []
                while i < n and lines[i].strip():
                    cue_lines.append(lines[i])
                    i += 1

                cue_text = "\n".join(cue_lines).strip()
                cues.append(
                    Cue(
                        start=start_ms,
                        end=end_ms,
                        text=cue_text,
                        index=len(cues) + 1,
                        identifier=identifier,
                        settings=settings_str,
                    )
                )
                continue

            # If unrecognized line outside cue, skip it
            i += 1

        return SubtitleDocument(
            format="vtt",
            cues=cues,
            vtt_header=vtt_header,
            vtt_styles=vtt_styles,
            vtt_notes=vtt_notes,
            vtt_regions=vtt_regions,
        )


class VttWriter(BaseSubtitleWriter):
    """Standard writer for WebVTT (.vtt) subtitle files."""

    def write(self, doc: SubtitleDocument) -> str:
        parts: list[str] = [doc.vtt_header]

        # Preserve REGION blocks
        parts.extend(doc.vtt_regions)

        # Preserve STYLE blocks
        parts.extend(doc.vtt_styles)

        # Preserve NOTE blocks (top-level)
        parts.extend(doc.vtt_notes)

        # Render cues
        for cue in doc.cues:
            cue_parts: list[str] = []
            if cue.identifier:
                cue_parts.append(cue.identifier)

            start_str = format_vtt_time(cue.start)
            end_str = format_vtt_time(cue.end)
            timing_line = f"{start_str} --> {end_str}"
            if cue.settings:
                timing_line += f" {cue.settings}"
            cue_parts.append(timing_line)
            cue_parts.append(cue.text)

            parts.append("\n".join(cue_parts))

        return "\n\n".join(parts) + "\n"
