"""Core data types and models for subtitle representations."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Cue:
    """Represents a single subtitle cue across formats."""

    start: int  # Start time in milliseconds
    end: int    # End time in milliseconds
    text: str   # Cue text content
    index: int | None = None  # Sequential index (SRT 1-based, etc.)
    identifier: str | None = None  # WebVTT cue identifier
    settings: str | None = None  # WebVTT cue settings (e.g., align:center)
    style: str = "Default"  # ASS style name
    actor: str = ""  # ASS speaker / name
    margin_l: int = 0  # ASS left margin
    margin_r: int = 0  # ASS right margin
    margin_v: int = 0  # ASS vertical margin
    effect: str = ""  # ASS effect
    layer: int = 0  # ASS layer
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> int:
        """Duration in milliseconds."""
        return self.end - self.start

    @property
    def is_empty(self) -> bool:
        """True if the cue contains only whitespace or is empty."""
        return not bool(self.text and self.text.strip())

    def clone(self) -> Cue:
        """Return a deep copy of the cue."""
        return copy.deepcopy(self)


@dataclass
class AssStyle:
    """Represents a single style definition in ASS [V4+ Styles]."""

    name: str = "Default"
    fontname: str = "Arial"
    fontsize: float = 20.0
    primary_colour: str = "&H00FFFFFF"
    secondary_colour: str = "&H000000FF"
    outline_colour: str = "&H00000000"
    back_colour: str = "&H00000000"
    bold: int = 0
    italic: int = 0
    underline: int = 0
    strikeout: int = 0
    scale_x: float = 100.0
    scale_y: float = 100.0
    spacing: float = 0.0
    angle: float = 0.0
    border_style: int = 1
    outline: float = 2.0
    shadow: float = 2.0
    alignment: int = 2
    margin_l: int = 10
    margin_r: int = 10
    margin_v: int = 10
    encoding: int = 1
    raw_line: str | None = None

    def to_ass_line(self) -> str:
        """Render style as ASS Style line."""
        if self.raw_line:
            return self.raw_line
        return (
            f"Style: {self.name},{self.fontname},{self.fontsize},"
            f"{self.primary_colour},{self.secondary_colour},{self.outline_colour},{self.back_colour},"
            f"{self.bold},{self.italic},{self.underline},{self.strikeout},"
            f"{self.scale_x},{self.scale_y},{self.spacing},{self.angle},"
            f"{self.border_style},{self.outline},{self.shadow},{self.alignment},"
            f"{self.margin_l},{self.margin_r},{self.margin_v},{self.encoding}"
        )


@dataclass
class SubtitleDocument:
    """Represents a parsed subtitle file with its cues and format metadata."""

    format: str  # "srt", "vtt", "ass"
    cues: list[Cue] = field(default_factory=list)
    encoding: str = "utf-8"

    # WebVTT specific metadata
    vtt_header: str = "WEBVTT"
    vtt_styles: list[str] = field(default_factory=list)
    vtt_notes: list[str] = field(default_factory=list)
    vtt_regions: list[str] = field(default_factory=list)

    # ASS/SSA specific metadata
    ass_script_info: list[tuple[str, str]] = field(default_factory=list)
    ass_styles: list[str] = field(default_factory=list)
    ass_events_format: list[str] = field(default_factory=list)
    ass_unknown_sections: list[tuple[str, list[str]]] = field(default_factory=list)

    @property
    def cue_count(self) -> int:
        """Total number of cues."""
        return len(self.cues)

    @property
    def total_duration(self) -> int:
        """Duration from time 0 to the end of the last cue in milliseconds."""
        if not self.cues:
            return 0
        return max(c.end for c in self.cues)

    def clone(self) -> SubtitleDocument:
        """Return a deep copy of the subtitle document."""
        return copy.deepcopy(self)
