"""Pure layout rules; hard spatial limits take precedence over reading targets."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import cache
from itertools import pairwise
from math import isfinite
from typing import Literal

from .models import Word, WordCue

Mode = Literal["words", "groups"]
_JOINERS = {"ve", "ama", "ki", "de", "da"}
_PUNCTUATION = ".,;:!?…"


def turkish_upper(text: str) -> str:
    return text.translate(str.maketrans("iı", "İI")).upper()


def _joiner(word: Word) -> bool:
    """True for a conjunction that dangles: one followed by punctuation closes its clause."""
    if word.text.endswith(tuple(_PUNCTUATION)):
        return False
    lowered = word.text.translate(str.maketrans("İI", "iı")).lower()
    return lowered.strip("\"'“”") in _JOINERS


@dataclass(frozen=True)
class LayoutConfig:
    max_chars: int = 18
    max_lines: int = 2
    pause_threshold: float = 0.6
    min_duration: float = 0.8
    max_cps: float = 18.0
    mode: Mode = "groups"
    upper: bool = False
    turkish_case: bool = True

    def __post_init__(self) -> None:
        if type(self.max_chars) is not int or self.max_chars < 1:
            raise ValueError("max_chars must be a positive integer.")
        if type(self.max_lines) is not int or not 1 <= self.max_lines <= 4:
            raise ValueError("max_lines must be an integer between 1 and 4.")
        for name in ("pause_threshold", "min_duration", "max_cps"):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive.")
        if self.mode not in ("words", "groups"):
            raise ValueError("mode must be words or groups.")
        if type(self.turkish_case) is not bool:
            raise ValueError("turkish_case must be a boolean.")


def _wrap(words: tuple[Word, ...], config: LayoutConfig) -> tuple[tuple[Word, ...], ...] | None:
    # A tiny bounded search avoids greedy breaks that strand a conjunction.
    @cache
    def solve(start: int, remaining: int) -> tuple[int, tuple[tuple[Word, ...], ...]] | None:
        if start == len(words):
            return 0, ()
        if remaining == 0:
            return None
        best = None
        length = -1
        for end in range(start + 1, len(words) + 1):
            length += len(words[end - 1].text) + 1
            if length > config.max_chars:
                break
            tail = solve(end, remaining - 1)
            if tail is None:
                continue
            penalty = (10000 if _joiner(words[end - 1]) else 0) + 100
            score = penalty + tail[0] + (config.max_chars - length) ** 2
            candidate = (score, (words[start:end],) + tail[1])
            if best is None or score < best[0]:
                best = candidate
        return best

    result = solve(0, config.max_lines)
    return result[1] if result else None


def _required(cue: WordCue, config: LayoutConfig) -> float:
    return max(config.min_duration, len(cue.text.replace("\n", " ")) / config.max_cps)


def layout(
    words: Sequence[Word], config: LayoutConfig | None = None, *, duration: float | None = None
) -> tuple[WordCue, ...]:
    """Pack timed words, merge short neighbours, then extend into available silence.

    Never reorder words or overlap cues. An indivisible oversized word is retained;
    ``layout_warnings`` exposes constraints that cannot be satisfied without data loss.
    ``duration`` caps the final cue at the media end; absent it, no tail is invented.
    """
    config = config or LayoutConfig()
    upper = turkish_upper if config.turkish_case else str.upper
    items = tuple(replace(w, text=upper(w.text)) if config.upper else w for w in words)
    if any(a.end > b.start for a, b in pairwise(items)):
        raise ValueError("Words must be chronological and non-overlapping.")
    if duration is not None and (
        not isfinite(duration) or duration < 0 or (items and duration < items[-1].end)
    ):
        raise ValueError("Media duration must be finite and contain all words.")
    if not items:
        return ()

    groups: list[tuple[Word, ...]] = []
    current: tuple[Word, ...] = ()
    for word in items:
        boundary = current and (
            config.mode == "words"
            or word.start - current[-1].end > config.pause_threshold
            or current[-1].text.endswith(tuple(_PUNCTUATION))
            or _wrap(current + (word,), config) is None
        )
        if boundary:
            # Keep a trailing conjunction with the next word if both fit together.
            carry = (
                current[-1:]
                if (
                    len(current) > 1
                    and _joiner(current[-1])
                    and word.start - current[-1].end <= config.pause_threshold
                )
                else ()
            )
            if carry and _wrap(carry + (word,), config) is not None:
                groups.append(current[:-1])
                current = carry
            else:
                groups.append(current)
                current = ()
        current += (word,)
    groups.append(current)
    cues = [WordCue(g[0].start, g[-1].end, _wrap(g, config) or (g,)) for g in groups]

    # Merge when either neighbour is too brief, but never across a long pause.
    index = 0
    while index + 1 < len(cues):
        left, right = cues[index : index + 2]
        lines = _wrap(left.words + right.words, config)
        short = any(c.end - c.start < _required(c, config) for c in (left, right))
        if short and lines and right.start - left.words[-1].end <= config.pause_threshold:
            cues[index : index + 2] = [WordCue(left.start, right.end, lines)]
            index = max(0, index - 1)
        else:
            index += 1
    for index, cue in enumerate(cues):
        limit = cues[index + 1].start if index + 1 < len(cues) else duration
        if limit is not None:
            cues[index] = replace(
                cue, end=min(limit, max(cue.end, cue.start + _required(cue, config)))
            )
    return tuple(cues)


def layout_warnings(
    cues: Sequence[WordCue], config: LayoutConfig
) -> list[dict[str, object]]:
    """Return local, machine-readable notices for unavoidable constraint violations."""
    warnings: list[dict[str, object]] = []
    for index, cue in enumerate(cues, 1):
        codes = []
        if any(len(line) > config.max_chars for line in cue.text.splitlines()):
            codes.append("long_word")
        if cue.end - cue.start + 1e-9 < config.min_duration:
            codes.append("short_duration")
        if len(cue.text.replace("\n", " ")) / (cue.end - cue.start) > config.max_cps + 1e-9:
            codes.append("reading_speed")
        if any(_joiner(line[-1]) for line in cue.lines):
            codes.append("trailing_conjunction")
        if codes:
            warnings.append({"cue": index, "codes": codes})
    return warnings
