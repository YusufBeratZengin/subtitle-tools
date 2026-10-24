"""Build core ``SubtitleDocument`` objects from word cues.

Formatting is delegated to the core SRT, WebVTT, and ASS writers. This module only
adds what those writers cannot know: escaping of untrusted decoder text, the
vertical-video ASS header, and per-word karaoke events.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from itertools import pairwise

from subtitle_tools.parsers import write
from subtitle_tools.parsers.ass import DEFAULT_STYLES_FORMAT
from subtitle_tools.time import format_ass_time
from subtitle_tools.types import Cue, SubtitleDocument

from .models import Word, WordCue, seconds_to_ms
from .style import Style

PLAY_RES = (1080, 1920)


def _plain(text: str) -> str:
    # SRT and WebVTT players interpret markup. Escape decoder text, never run it as tags.
    return html.escape(text, quote=False)


def _ass_text(text: str) -> str:
    # Use fullwidth lookalikes so untrusted decoder text cannot introduce overrides
    # or ASS hard breaks. Intentional breaks are added by the core writer.
    return text.translate(str.maketrans("\\{}", "＼｛｝"))


def _render(cue: WordCue, active: Word | None, style: Style) -> str:
    def token(word: Word) -> str:
        text = _ass_text(word.text)
        if word is active:
            # Inline color syntax uses BBGGRR; the style header also carries alpha.
            color = style.highlight_color[4:]
            alpha = style.highlight_color[2:4]
            return f"{{\\1c&H{color}&\\1a&H{alpha}&}}{text}{{\\rDefault}}"
        return text

    return "\n".join(" ".join(token(w) for w in line) for line in cue.lines)


def _ass_events(cues: Sequence[WordCue], style: Style, karaoke: bool) -> list[Cue]:
    events: list[Cue] = []
    for cue in cues:
        cuts = sorted(
            {cue.start, cue.end}
            | ({time for w in cue.words for time in (w.start, w.end)} if karaoke else set())
        )
        for start, end in pairwise(cuts):
            start_ms, end_ms = seconds_to_ms(start), seconds_to_ms(end)
            if format_ass_time(start_ms) == format_ass_time(end_ms):
                continue  # shorter than one ASS centisecond
            active = next((w for w in cue.words if w.start <= start < w.end), None)
            text = _render(cue, active if karaoke else None, style)
            events.append(Cue(start=start_ms, end=end_ms, text=text, index=len(events) + 1))
    return events


def to_document(
    cues: Sequence[WordCue],
    fmt: str,
    *,
    style: Style | None = None,
    karaoke: bool = False,
) -> SubtitleDocument:
    """Return a core document for ``srt``, ``vtt``, or ``ass``."""
    if fmt in ("srt", "vtt"):
        return SubtitleDocument(
            format=fmt,
            cues=[cue.to_cue(text=_plain(cue.text), index=i) for i, cue in enumerate(cues, 1)],
        )
    if fmt != "ass":
        raise ValueError(f"Unsupported subtitle format: '{fmt}'. Supported: srt, vtt, ass")
    style = style or Style()
    return SubtitleDocument(
        format="ass",
        cues=_ass_events(cues, style, karaoke),
        ass_script_info=[
            ("ScriptType", "v4.00+"),
            ("PlayResX", str(PLAY_RES[0])),
            ("PlayResY", str(PLAY_RES[1])),
            ("WrapStyle", "2"),
            ("ScaledBorderAndShadow", "yes"),
        ],
        ass_styles=[DEFAULT_STYLES_FORMAT, style.to_ass_style().to_ass_line()],
    )


def srt(cues: Sequence[WordCue]) -> str:
    return write(to_document(cues, "srt"), "srt")


def vtt(cues: Sequence[WordCue]) -> str:
    return write(to_document(cues, "vtt"), "vtt")


def ass(cues: Sequence[WordCue], *, style: Style | None = None, karaoke: bool = False) -> str:
    return write(to_document(cues, "ass", style=style, karaoke=karaoke), "ass")
