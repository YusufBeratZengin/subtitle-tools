"""subtitle-tools — A zero-dependency Python library and CLI for subtitle conversion, manipulation, and linting."""

from subtitle_tools.encoding import (
    ENCODING_FALLBACK_ORDER,
    detect_encoding,
    read_subtitle_file,
    write_subtitle_file,
)
from subtitle_tools.lint import (
    LintConfig,
    LintIssue,
    Severity,
    auto_fix_tags,
    fix_document,
    lint_document,
)
from subtitle_tools.operations import (
    convert,
    join,
    merge,
    renumber,
    scale,
    shift,
    split,
    strip_formatting_tags,
    strip_tags,
)
from subtitle_tools.parsers import guess_format, parse, write
from subtitle_tools.time import (
    format_ass_time,
    format_srt_time,
    format_vtt_time,
    parse_offset,
    parse_time,
)
from subtitle_tools.types import AssStyle, Cue, SubtitleDocument

__version__ = "0.1.0"

__all__ = [
    # Types
    "Cue",
    "SubtitleDocument",
    "AssStyle",
    # Parsers and writers
    "parse",
    "write",
    "guess_format",
    # Operations
    "convert",
    "shift",
    "scale",
    "merge",
    "split",
    "join",
    "renumber",
    "strip_tags",
    "strip_formatting_tags",
    # Linting & fixing
    "lint_document",
    "fix_document",
    "LintConfig",
    "LintIssue",
    "Severity",
    "auto_fix_tags",
    # Encoding & file I/O
    "detect_encoding",
    "read_subtitle_file",
    "write_subtitle_file",
    "ENCODING_FALLBACK_ORDER",
    # Time utilities
    "parse_time",
    "parse_offset",
    "format_srt_time",
    "format_vtt_time",
    "format_ass_time",
]
