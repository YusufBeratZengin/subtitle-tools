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

__version__ = "0.2.0"

__all__ = [
    "ENCODING_FALLBACK_ORDER",
    "AssStyle",
    "Cue",
    "LintConfig",
    "LintIssue",
    "Severity",
    "SubtitleDocument",
    "auto_fix_tags",
    "convert",
    "detect_encoding",
    "fix_document",
    "format_ass_time",
    "format_srt_time",
    "format_vtt_time",
    "guess_format",
    "join",
    "lint_document",
    "merge",
    "parse",
    "parse_offset",
    "parse_time",
    "read_subtitle_file",
    "renumber",
    "scale",
    "shift",
    "split",
    "strip_formatting_tags",
    "strip_tags",
    "write",
    "write_subtitle_file",
]
