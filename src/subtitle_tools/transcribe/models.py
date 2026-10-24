"""Immutable word-timing values used by recognition and layout.

``WordCue`` is a layout intermediate: it keeps each line's timed words so the ASS
karaoke renderer can highlight the active word. Serialization always goes through
the core :class:`subtitle_tools.types.Cue` via :meth:`WordCue.to_cue`.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from math import isfinite

from subtitle_tools.types import Cue


def seconds_to_ms(seconds: float) -> int:
    """Convert float seconds to the integer milliseconds used by the core types."""
    return round(seconds * 1000)


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str
    prob: float = 1.0

    def __post_init__(self) -> None:
        if not isfinite(self.start) or not isfinite(self.end) or not 0 <= self.start < self.end:
            raise ValueError("Word timestamps must be finite, non-negative, and increasing.")
        if not self.text or any(char.isspace() for char in self.text):
            raise ValueError("Word text must be a non-empty token without whitespace.")
        if not isfinite(self.prob) or not 0 <= self.prob <= 1:
            raise ValueError("Word probability must be between 0 and 1.")


@dataclass(frozen=True)
class WordCue:
    start: float
    end: float
    lines: tuple[tuple[Word, ...], ...]

    def __post_init__(self) -> None:
        if not isfinite(self.start) or not isfinite(self.end) or not 0 <= self.start < self.end:
            raise ValueError("Cue timestamps must be finite, non-negative, and increasing.")
        if not self.lines or any(not line for line in self.lines):
            raise ValueError("Cue lines must not be empty.")
        words = self.words
        if self.start > words[0].start or self.end < words[-1].end:
            raise ValueError("Cue must contain its word timestamps.")
        if any(left.end > right.start for left, right in pairwise(words)):
            raise ValueError("Cue words must be chronological and non-overlapping.")

    @property
    def words(self) -> tuple[Word, ...]:
        return tuple(word for line in self.lines for word in line)

    @property
    def text(self) -> str:
        return "\n".join(" ".join(word.text for word in line) for line in self.lines)

    def to_cue(self, *, text: str | None = None, index: int | None = None) -> Cue:
        """Return the core millisecond ``Cue``; ``text`` overrides the joined words."""
        return Cue(
            start=seconds_to_ms(self.start),
            end=seconds_to_ms(self.end),
            text=self.text if text is None else text,
            index=index,
        )
