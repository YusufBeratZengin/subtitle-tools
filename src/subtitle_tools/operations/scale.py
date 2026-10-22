"""Framerate and duration scaling operations for subtitles."""

from __future__ import annotations

from subtitle_tools.types import SubtitleDocument

COMMON_FRAMERATES: dict[str, float] = {
    "23.976": 24000.0 / 1001.0,
    "23.98": 24000.0 / 1001.0,
    "24": 24.0,
    "25": 25.0,
    "29.97": 30000.0 / 1001.0,
    "30": 30.0,
    "50": 50.0,
    "59.94": 60000.0 / 1001.0,
    "60": 60.0,
}


def parse_fps(fps: float | str) -> float:
    """Parse a framerate value or recognized string into a float."""
    if isinstance(fps, (int, float)):
        return float(fps)
    key = str(fps).strip().lower()
    if key in COMMON_FRAMERATES:
        return COMMON_FRAMERATES[key]
    try:
        return float(key)
    except ValueError:
        raise ValueError(f"Invalid framerate: '{fps}'")


def scale(
    doc: SubtitleDocument,
    factor: float | None = None,
    from_fps: float | str | None = None,
    to_fps: float | str | None = None,
) -> SubtitleDocument:
    """Scale subtitle timestamps by a multiplier or framerate ratio.

    When converting video from from_fps to to_fps (e.g. 23.976 to 25 PAL speedup),
    timestamps scale by (from_fps / to_fps).

    Args:
        doc: SubtitleDocument to scale.
        factor: Direct multiplier applied to timestamps.
        from_fps: Source framerate (e.g. 23.976, 25, 29.97).
        to_fps: Target framerate (e.g. 25, 23.976, 24).

    Returns:
        A new SubtitleDocument with scaled timestamps.
    """
    if factor is not None:
        multiplier = float(factor)
    elif from_fps is not None and to_fps is not None:
        src = parse_fps(from_fps)
        dst = parse_fps(to_fps)
        if dst <= 0:
            raise ValueError("Target framerate must be positive")
        multiplier = src / dst
    else:
        raise ValueError("Must provide either 'factor' or both 'from_fps' and 'to_fps'.")

    new_doc = doc.clone()
    for cue in new_doc.cues:
        cue.start = int(round(cue.start * multiplier))
        cue.end = int(round(cue.end * multiplier))

    return new_doc
