"""Offline, word-timed subtitles for short vertical videos (``subtitle-tools[transcribe]``).

Importing this package never loads faster-whisper or a model; only
:func:`transcribe` does, and it reads models from local files only.
"""

from .engine import Transcript, transcribe
from .layout import LayoutConfig, layout, layout_warnings, turkish_upper
from .models import Word, WordCue
from .style import Style, load_style
from .writers import to_document

__all__ = [
    "LayoutConfig",
    "Style",
    "Transcript",
    "Word",
    "WordCue",
    "layout",
    "layout_warnings",
    "load_style",
    "to_document",
    "transcribe",
    "turkish_upper",
]
