"""Time representation, parsing, and formatting utilities for subtitles."""

from __future__ import annotations

import re

# Regex patterns for time parsing
_RE_SRT_VTT = re.compile(
    r"^(?:(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{1,2}):)?(?P<seconds>\d{1,2})[.,](?P<millis>\d{1,3})$"
)
_RE_ASS = re.compile(
    r"^(?P<hours>\d{1,2}):(?P<minutes>\d{2}):(?P<seconds>\d{2})\.(?P<centis>\d{1,2})$"
)
_RE_OFFSET = re.compile(
    r"^(?P<sign>[+-])?(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|s|m|h)?$",
    re.IGNORECASE,
)


def parse_time(time_str: str) -> int:
    """Parse a timestamp string into integer milliseconds.

    Supports SRT (00:01:23,456), WebVTT (00:01:23.456 or 01:23.456),
    ASS (0:01:23.45), and offset strings (1500ms, 1.5s).

    Raises:
        ValueError: If time_str cannot be parsed.
    """
    s = time_str.strip()
    if not s:
        raise ValueError("Empty time string")

    # Check for sign prefix (e.g. -00:01:00.000 or -1500ms)
    sign = 1
    if s.startswith("-"):
        sign = -1
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()

    # Try offset with unit (e.g. 1500ms, 2.5s)
    offset_match = _RE_OFFSET.match(s)
    if offset_match and offset_match.group("unit"):
        val = float(offset_match.group("value"))
        unit = (offset_match.group("unit") or "ms").lower()
        if unit == "ms":
            ms = round(val)
        elif unit == "s":
            ms = round(val * 1000)
        elif unit == "m":
            ms = round(val * 60_000)
        elif unit == "h":
            ms = round(val * 3_600_000)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
        return sign * ms

    # Try ASS time format (H:MM:SS.cc)
    ass_match = _RE_ASS.match(s)
    if ass_match:
        h = int(ass_match.group("hours"))
        m = int(ass_match.group("minutes"))
        sec = int(ass_match.group("seconds"))
        c_str = ass_match.group("centis").ljust(2, "0")
        cs = int(c_str[:2])
        total_ms = (h * 3600 + m * 60 + sec) * 1000 + cs * 10
        return sign * total_ms

    # Try SRT / WebVTT timestamp format
    srt_match = _RE_SRT_VTT.match(s)
    if srt_match:
        h_str = srt_match.group("hours")
        m_str = srt_match.group("minutes")
        sec_str = srt_match.group("seconds")
        ms_str = srt_match.group("millis").ljust(3, "0")[:3]

        sec = int(sec_str)
        m = int(m_str) if m_str is not None else 0
        h = int(h_str) if h_str is not None else 0
        ms = int(ms_str)

        total_ms = (h * 3600 + m * 60 + sec) * 1000 + ms
        return sign * total_ms

    # Try plain integer/float seconds or milliseconds
    try:
        val = float(s)
        # If float with decimal or integer without unit, treat as ms if integer > 1000 or seconds if has decimal
        # But to be safe and deterministic: if no unit and just number, treat as milliseconds
        return sign * round(val)
    except ValueError:
        pass

    raise ValueError(f"Invalid timestamp format: '{time_str}'")


def parse_offset(offset_str: str) -> int:
    """Parse time offset string like '+1500ms', '-200ms', '1.5s', '-00:00:02.000'.

    Returns integer milliseconds.
    """
    return parse_time(offset_str)


def split_ms(ms: int) -> tuple[int, int, int, int]:
    """Split milliseconds into (hours, minutes, seconds, milliseconds).

    If ms < 0, returns (0, 0, 0, 0).
    """
    if ms < 0:
        return 0, 0, 0, 0

    total_seconds, millis = divmod(ms, 1000)
    total_minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(total_minutes, 60)
    return hours, minutes, seconds, millis


def format_srt_time(ms: int) -> str:
    """Format milliseconds into SubRip timestamp: HH:MM:SS,mmm"""
    h, m, s, milli = split_ms(ms)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def format_vtt_time(ms: int) -> str:
    """Format milliseconds into WebVTT timestamp: HH:MM:SS.mmm"""
    h, m, s, milli = split_ms(ms)
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


def format_ass_time(ms: int) -> str:
    """Format milliseconds into ASS timestamp: H:MM:SS.cc"""
    if ms < 0:
        return "0:00:00.00"

    # Centiseconds rounded
    total_cs = round(ms / 10.0)
    total_seconds, cs = divmod(total_cs, 100)
    total_minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}.{cs:02d}"
