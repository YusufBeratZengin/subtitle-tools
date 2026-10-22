"""Encoding detection and file I/O utilities for legacy and modern subtitle files."""

from __future__ import annotations

import codecs
from pathlib import Path
from typing import Final

# Documented fallback order for legacy encoding detection
ENCODING_FALLBACK_ORDER: Final[tuple[str, ...]] = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "cp1254",
    "latin-1",
)

# Turkish Windows-1254 characteristic bytes:
# 0xF0 (ğ), 0xFD (ı), 0xFE (ş), 0xD0 (Ğ), 0xDD (İ), 0xDE (Ş)
_CP1254_TURKISH_BYTES: Final[set[int]] = {0xF0, 0xFD, 0xFE, 0xD0, 0xDD, 0xDE}


def detect_encoding(raw_bytes: bytes) -> str:
    """Detect the text encoding of raw subtitle bytes.

    Fallback detection order:
    1. utf-8-sig: Checked first via the UTF-8 Byte Order Mark (BOM: 0xEF, 0xBB, 0xBF).
    2. utf-8: Strict UTF-8 decoding without BOM.
    3. cp1254 / cp1252:
       If non-UTF-8 bytes contain Windows-1254 Turkish characteristic characters
       (ğ, ı, ş, Ğ, İ, Ş), cp1254 is selected.
       Otherwise, Windows-1252 (Western European) is used.
    4. cp1254: Fallback if cp1252 decode fails on undefined bytes.
    5. latin-1: ISO-8859-1 fallback, which maps all 256 bytes safely.

    Returns:
        The detected encoding name as a lowercase string.
    """
    if raw_bytes.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"

    # Try strict utf-8
    try:
        raw_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Check if legacy non-UTF8 text contains Turkish CP1254 signature characters
    has_turkish_cp1254 = any(b in _CP1254_TURKISH_BYTES for b in raw_bytes)
    if has_turkish_cp1254:
        try:
            raw_bytes.decode("cp1254")
            return "cp1254"
        except UnicodeDecodeError:
            pass

    # Try cp1252 (Western European)
    try:
        raw_bytes.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        pass

    # Try cp1254 (Turkish Windows ANSI)
    try:
        raw_bytes.decode("cp1254")
        return "cp1254"
    except UnicodeDecodeError:
        pass

    # Final fallback: latin-1 (always succeeds for any byte stream)
    return "latin-1"


def check_mixed_newlines(raw_bytes: bytes) -> bool:
    """Check if raw byte content contains mixed newline conventions (CRLF and solitary LF)."""
    has_crlf = b"\r\n" in raw_bytes
    # Remove all \r\n to see if solitary \n or \r exists
    stripped = raw_bytes.replace(b"\r\n", b"")
    has_lf = b"\n" in stripped
    has_cr = b"\r" in stripped
    return (has_crlf and has_lf) or (has_crlf and has_cr) or (has_lf and has_cr)


def read_subtitle_file(
    path: str | Path,
    encoding: str | None = None,
) -> tuple[str, str, bool, bool]:
    """Read a subtitle file, automatically detecting encoding if not specified.

    Returns:
        Tuple of:
        - text (normalized string with BOM removed)
        - detected_or_used_encoding (str)
        - has_bom (bool)
        - has_mixed_newlines (bool)
    """
    file_path = Path(path)
    raw_bytes = file_path.read_bytes()

    has_bom = raw_bytes.startswith(codecs.BOM_UTF8)
    has_mixed_newlines = check_mixed_newlines(raw_bytes)

    if encoding:
        enc = encoding.lower()
    else:
        enc = detect_encoding(raw_bytes)

    # Decode text
    if enc in ("utf-8-sig", "utf-8") and has_bom:
        text = raw_bytes.decode("utf-8-sig")
    else:
        text = raw_bytes.decode(enc)

    return text, enc, has_bom, has_mixed_newlines


def write_subtitle_file(
    path: str | Path,
    content: str,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> None:
    """Write subtitle text to a file with specified encoding and line separator."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize line endings
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        normalized = normalized.replace("\n", newline)

    file_path.write_text(normalized, encoding=encoding)
