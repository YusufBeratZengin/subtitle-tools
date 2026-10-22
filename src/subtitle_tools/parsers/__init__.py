"""Parser and writer registry for subtitle formats."""

from __future__ import annotations

from pathlib import Path

from subtitle_tools.parsers.ass import AssParser, AssWriter
from subtitle_tools.parsers.base import BaseSubtitleParser, BaseSubtitleWriter
from subtitle_tools.parsers.srt import SrtParser, SrtWriter
from subtitle_tools.parsers.vtt import VttParser, VttWriter
from subtitle_tools.types import SubtitleDocument

_PARSERS: dict[str, type[BaseSubtitleParser]] = {
    "srt": SrtParser,
    "vtt": VttParser,
    "webvtt": VttParser,
    "ass": AssParser,
    "ssa": AssParser,
}

_WRITERS: dict[str, type[BaseSubtitleWriter]] = {
    "srt": SrtWriter,
    "vtt": VttWriter,
    "webvtt": VttWriter,
    "ass": AssWriter,
    "ssa": AssWriter,
}


def guess_format(path_or_name: str | Path, content: str | None = None) -> str:
    """Guess subtitle format based on file extension and/or text content."""
    suffix = Path(path_or_name).suffix.lower().lstrip(".")
    if suffix in _PARSERS:
        # Normalize ssa -> ass, webvtt -> vtt
        if suffix == "ssa":
            return "ass"
        if suffix == "webvtt":
            return "vtt"
        return suffix

    if content:
        stripped = content.strip()
        if stripped.startswith("WEBVTT"):
            return "vtt"
        if "[Script Info]" in stripped or "[Events]" in stripped:
            return "ass"
        # SRT typically has digits and "-->"
        if "-->" in stripped:
            return "srt"

    raise ValueError(f"Could not determine subtitle format for: {path_or_name}")


def get_parser(fmt: str) -> BaseSubtitleParser:
    """Retrieve parser instance for given format."""
    key = fmt.lower()
    if key not in _PARSERS:
        raise ValueError(f"Unsupported subtitle format: '{fmt}'. Supported: srt, vtt, ass")
    return _PARSERS[key]()


def get_writer(fmt: str) -> BaseSubtitleWriter:
    """Retrieve writer instance for given format."""
    key = fmt.lower()
    if key not in _WRITERS:
        raise ValueError(f"Unsupported subtitle format: '{fmt}'. Supported: srt, vtt, ass")
    return _WRITERS[key]()


def parse(text: str, fmt: str) -> SubtitleDocument:
    """Parse subtitle text of given format into a SubtitleDocument."""
    parser = get_parser(fmt)
    doc = parser.parse(text)
    # Ensure doc.format is canonical
    if fmt.lower() in ("vtt", "webvtt"):
        doc.format = "vtt"
    elif fmt.lower() in ("ass", "ssa"):
        doc.format = "ass"
    else:
        doc.format = "srt"
    return doc


def write(doc: SubtitleDocument, fmt: str | None = None) -> str:
    """Serialize a SubtitleDocument into text using original or target format."""
    target_format = fmt or doc.format
    writer = get_writer(target_format)
    return writer.write(doc)
