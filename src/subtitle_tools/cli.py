"""Command-line interface for subtitle-tools (subtool)."""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn, TypedDict

from subtitle_tools import __version__
from subtitle_tools.encoding import read_subtitle_file, write_subtitle_file
from subtitle_tools.lint import LintConfig, fix_document, lint_document
from subtitle_tools.operations import (
    convert as op_convert,
)
from subtitle_tools.operations import (
    join as op_join,
)
from subtitle_tools.operations import (
    merge as op_merge,
)
from subtitle_tools.operations import (
    renumber as op_renumber,
)
from subtitle_tools.operations import (
    scale as op_scale,
)
from subtitle_tools.operations import (
    shift as op_shift,
)
from subtitle_tools.operations import (
    split as op_split,
)
from subtitle_tools.operations import (
    strip_tags as op_strip_tags,
)
from subtitle_tools.operations.scale import parse_fps
from subtitle_tools.parsers import guess_format, parse, write
from subtitle_tools.time import format_srt_time, parse_time
from subtitle_tools.transcribe.cli import add_parser as add_transcribe_parser


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, f"{self.prog}: error: {' '.join(message.splitlines())}\n")


class _UsageError(ValueError):
    """Invalid command-line format selection."""


def _guess_cli_format(path: Path, content: str | None = None) -> str:
    try:
        return guess_format(path, content)
    except ValueError as exc:
        raise _UsageError(str(exc)) from exc


def _positive_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def _timestamp(value: str) -> int:
    try:
        return parse_time(value)
    except (ValueError, OverflowError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _framerate(value: str) -> float:
    try:
        fps = parse_fps(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not math.isfinite(fps) or fps <= 0:
        raise argparse.ArgumentTypeError("framerate must be finite and positive")
    return fps


class _LintResult(TypedDict):
    file: str
    issues: list[dict[str, Any]]
    fixes_applied: int


def _expand_globs(patterns: Sequence[str]) -> list[Path]:
    """Expand wildcards on Windows and collect unique existing file paths."""
    resolved: list[Path] = []
    seen: set[Path] = set()

    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            matched = glob.glob(pattern, recursive=True)
            for m in matched:
                p = Path(m).resolve()
                if p.is_file() and p not in seen:
                    seen.add(p)
                    resolved.append(p)
        else:
            p = Path(pattern).resolve()
            if p not in seen:
                seen.add(p)
                resolved.append(p)

    return resolved


def _load_doc(path: Path, fmt: str | None = None, encoding: str | None = None):
    text, enc, has_bom, has_mixed_newlines = read_subtitle_file(path, encoding=encoding)
    file_fmt = fmt or _guess_cli_format(path, text)
    doc = parse(text, file_fmt)
    doc.encoding = enc
    return doc, enc, has_bom, has_mixed_newlines


def _save_doc(doc, out_path: Path | None, target_fmt: str | None = None, in_place: bool = False, original_path: Path | None = None) -> None:
    output_content = write(doc, target_fmt)
    if out_path:
        write_subtitle_file(out_path, output_content, encoding=doc.encoding)
    elif in_place and original_path:
        write_subtitle_file(original_path, output_content, encoding=doc.encoding)
    else:
        sys.stdout.write(output_content)


def cmd_convert(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    out_path = Path(args.output).resolve()

    if not in_path.is_file():
        sys.stderr.write(f"Error: Input file not found: {in_path}\n")
        return 1

    from_fmt = args.from_format or _guess_cli_format(in_path)
    to_fmt = args.to_format or _guess_cli_format(out_path)

    doc, _enc, _, _ = _load_doc(in_path, fmt=from_fmt, encoding=args.encoding)
    converted_doc = op_convert(doc, target_format=to_fmt)
    converted_doc.encoding = "utf-8"

    write_subtitle_file(out_path, write(converted_doc, to_fmt), encoding="utf-8")
    return 0


def cmd_shift(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        sys.stderr.write(f"Error: Input file not found: {in_path}\n")
        return 1

    doc, _, _, _ = _load_doc(in_path, encoding=args.encoding)

    shifted_doc = op_shift(doc, by_ms=args.by, to_ms=args.to, drop_negative=args.drop_negative)

    out_p = Path(args.output).resolve() if args.output else None
    _save_doc(shifted_doc, out_p, in_place=args.in_place, original_path=in_path)
    return 0


def cmd_scale(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        sys.stderr.write(f"Error: Input file not found: {in_path}\n")
        return 1

    doc, _, _, _ = _load_doc(in_path, encoding=args.encoding)
    scaled_doc = op_scale(
        doc,
        factor=args.factor,
        from_fps=args.from_fps,
        to_fps=args.to_fps,
    )

    out_p = Path(args.output).resolve() if args.output else None
    _save_doc(scaled_doc, out_p, in_place=args.in_place, original_path=in_path)
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    in1_path = Path(args.input1).resolve()
    in2_path = Path(args.input2).resolve()
    out_path = Path(args.output).resolve()

    if not in1_path.is_file():
        sys.stderr.write(f"Error: Primary file not found: {in1_path}\n")
        return 1
    if not in2_path.is_file():
        sys.stderr.write(f"Error: Secondary file not found: {in2_path}\n")
        return 1

    doc1, _, _, _ = _load_doc(in1_path, encoding=args.encoding)
    doc2, _, _, _ = _load_doc(in2_path, encoding=args.encoding)

    sep = args.separator.replace(r"\n", "\n")
    merged_doc = op_merge(doc1, doc2, separator=sep, timing=args.timing)

    out_fmt = _guess_cli_format(out_path)
    write_subtitle_file(out_path, write(merged_doc, out_fmt), encoding="utf-8")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        sys.stderr.write(f"Error: Input file not found: {in_path}\n")
        return 1

    doc, _, _, _ = _load_doc(in_path, encoding=args.encoding)
    chunks = op_split(doc, duration_ms=args.duration, relative_times=not args.keep_absolute)

    prefix = args.output or in_path.stem
    ext = in_path.suffix or f".{doc.format}"
    parent = in_path.parent

    for idx, chunk in enumerate(chunks, 1):
        target = parent / f"{prefix}_part{idx:02d}{ext}"
        write_subtitle_file(target, write(chunk), encoding="utf-8")
        sys.stdout.write(f"Created: {target.name} ({len(chunk.cues)} cues)\n")

    return 0


def cmd_join(args: argparse.Namespace) -> int:
    files = _expand_globs(args.inputs)
    if not files:
        sys.stderr.write("Error: No input files provided for join\n")
        return 1

    out_path = Path(args.output).resolve()
    gap = args.gap

    docs = []
    for f in files:
        if not f.is_file():
            sys.stderr.write(f"Error: File not found: {f}\n")
            return 1
        d, _, _, _ = _load_doc(f, encoding=args.encoding)
        docs.append(d)

    joined_doc = op_join(docs, gap_ms=gap, shift_sequential=not args.no_shift)
    out_fmt = _guess_cli_format(out_path)
    write_subtitle_file(out_path, write(joined_doc, out_fmt), encoding="utf-8")
    return 0


def cmd_renumber(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        sys.stderr.write(f"Error: Input file not found: {in_path}\n")
        return 1

    doc, _, _, _ = _load_doc(in_path, encoding=args.encoding)
    renumbered_doc = op_renumber(doc, start_index=args.start)

    out_p = Path(args.output).resolve() if args.output else None
    _save_doc(renumbered_doc, out_p, in_place=args.in_place, original_path=in_path)
    return 0


def cmd_strip_tags(args: argparse.Namespace) -> int:
    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        sys.stderr.write(f"Error: Input file not found: {in_path}\n")
        return 1

    doc, _, _, _ = _load_doc(in_path, encoding=args.encoding)
    stripped_doc = op_strip_tags(doc)

    out_p = Path(args.output).resolve() if args.output else None
    _save_doc(stripped_doc, out_p, in_place=args.in_place, original_path=in_path)
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    files = _expand_globs(args.files)
    if not files:
        sys.stderr.write("Error: No subtitle files matched the input pattern\n")
        return 1

    config = LintConfig(
        max_cps=args.max_cps,
        max_line_length=args.max_line_length,
        max_lines=args.max_lines,
        min_duration_ms=args.min_duration,
        max_duration_ms=args.max_duration,
    )

    results: list[_LintResult] = []
    has_errors = False

    for file_path in files:
        try:
            doc, _enc, has_bom, has_mixed_newlines = _load_doc(file_path, encoding=args.encoding)
        except Exception as exc:  # noqa: BLE001 -- Report any per-file failure and continue the batch.
            results.append({
                "file": str(file_path),
                "issues": [{
                    "rule_id": "parse-error",
                    "severity": "error",
                    "message": f"Failed to parse file: {exc}",
                    "fixable": False,
                }],
                "fixes_applied": 0,
            })
            has_errors = True
            continue

        issues = lint_document(doc, config=config, has_bom=has_bom, has_mixed_newlines=has_mixed_newlines)
        fixes_applied = 0

        if args.fix:
            fixed_doc, fixes_applied = fix_document(doc, config=config)
            # Re-lint to report remaining issues
            remaining_issues = lint_document(fixed_doc, config=config, has_bom=False, has_mixed_newlines=False)
            if fixes_applied > 0 or has_bom or has_mixed_newlines:
                write_subtitle_file(file_path, write(fixed_doc), encoding="utf-8")
            issues = remaining_issues

        file_errors = any(i.severity == "error" for i in issues)
        if file_errors or (args.strict and issues):
            has_errors = True

        results.append({
            "file": str(file_path),
            "issues": [i.to_dict() for i in issues],
            "fixes_applied": fixes_applied,
        })

    if args.format == "json":
        sys.stdout.write(json.dumps(results, indent=2) + "\n")
    else:
        for item in results:
            file_p = Path(item["file"])
            try:
                path_str = str(file_p.relative_to(Path.cwd()))
            except (ValueError, RuntimeError):
                path_str = str(file_p)
            file_issues = item["issues"]
            fixes = item["fixes_applied"]

            sys.stdout.write(f"\n{path_str}:\n")
            if fixes > 0:
                sys.stdout.write(f"  Fixed {fixes} issue(s) automatically\n")

            if not file_issues:
                sys.stdout.write("  No issues found.\n")
                continue

            for issue in file_issues:
                sev = issue["severity"].upper()
                rule = issue["rule_id"]
                msg = issue["message"]
                cue_str = f" [Cue #{issue['cue_index']}]" if "cue_index" in issue else ""
                sys.stdout.write(f"  [{sev}] {rule}{cue_str}: {msg}\n")

    return 1 if has_errors else 0


def cmd_info(args: argparse.Namespace) -> int:
    files = _expand_globs(args.files)
    if not files:
        sys.stderr.write("Error: No files found\n")
        return 1

    for file_path in files:
        try:
            doc, enc, has_bom, has_mixed = _load_doc(file_path, encoding=args.encoding)
            dur_str = format_srt_time(doc.total_duration)
            bom_str = " (BOM present)" if has_bom else ""
            mixed_str = " (mixed newlines)" if has_mixed else ""
            sys.stdout.write(
                f"{file_path.name}:\n"
                f"  Format:   {doc.format.upper()}\n"
                f"  Encoding: {enc}{bom_str}{mixed_str}\n"
                f"  Cues:     {len(doc.cues)}\n"
                f"  Duration: {dur_str} ({doc.total_duration}ms)\n"
            )
        except Exception as exc:  # noqa: BLE001 -- Report any per-file failure and continue the batch.
            sys.stderr.write(f"{file_path.name}: Failed to read ({exc})\n")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="subtool",
        description="A zero-dependency Python CLI to convert, fix, and lint subtitle files (SRT, WebVTT, ASS).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # convert
    p_conv = subparsers.add_parser("convert", help="Convert subtitle file between formats")
    p_conv.add_argument("input", help="Source subtitle file")
    p_conv.add_argument("output", help="Target subtitle file")
    p_conv.add_argument("--from-format", choices=["srt", "vtt", "ass"], help="Explicit source format")
    p_conv.add_argument("--to-format", choices=["srt", "vtt", "ass"], help="Explicit target format")
    p_conv.add_argument("--encoding", help="Source file encoding")
    p_conv.set_defaults(func=cmd_convert)

    # shift
    p_shift = subparsers.add_parser("shift", help="Shift subtitle timestamps by an offset or alignment")
    p_shift.add_argument("input", help="Input subtitle file")
    p_shift.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p_shift.add_argument("-i", "--in-place", action="store_true", help="Modify input file in place")
    shift_mode = p_shift.add_mutually_exclusive_group(required=True)
    shift_mode.add_argument("--by", type=_timestamp, help="Shift offset (e.g. +1500ms, -2s, 00:01:00.000)")
    shift_mode.add_argument("--to", type=_timestamp, help="Align first cue to this timestamp (e.g. 00:01:00.000)")
    p_shift.add_argument("--drop-negative", action="store_true", help="Drop cues shifted before 0ms")
    p_shift.add_argument("--encoding", help="File encoding")
    p_shift.set_defaults(func=cmd_shift)

    # scale
    p_scale = subparsers.add_parser("scale", help="Scale subtitle timing (e.g., framerate conversion 23.976 <-> 25)")
    p_scale.add_argument("input", help="Input subtitle file")
    p_scale.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p_scale.add_argument("-i", "--in-place", action="store_true", help="Modify input file in place")
    scale_mode = p_scale.add_mutually_exclusive_group(required=True)
    scale_mode.add_argument("--from-fps", type=_framerate, help="Source framerate (e.g. 23.976, 25)")
    p_scale.add_argument("--to-fps", type=_framerate, help="Target framerate (e.g. 25, 23.976)")
    scale_mode.add_argument("--factor", type=_positive_number, help="Direct timing multiplier factor")
    p_scale.add_argument("--encoding", help="File encoding")
    p_scale.set_defaults(func=cmd_scale, command_parser=p_scale)

    # merge
    p_merge = subparsers.add_parser("merge", help="Merge two subtitle files into stacked dual-language cues")
    p_merge.add_argument("input1", help="Primary subtitle file (top)")
    p_merge.add_argument("input2", help="Secondary subtitle file (bottom)")
    p_merge.add_argument("-o", "--output", required=True, help="Output subtitle file path")
    p_merge.add_argument("--separator", default=r"\n", help="Separator between lines (default: newline)")
    p_merge.add_argument("--timing", choices=["union", "primary", "secondary"], default="union", help="Timing strategy")
    p_merge.add_argument("--encoding", help="File encoding")
    p_merge.set_defaults(func=cmd_merge)

    # split
    p_split = subparsers.add_parser("split", help="Split subtitle file by duration intervals")
    p_split.add_argument("input", help="Input subtitle file")
    p_split.add_argument("--duration", required=True, type=_timestamp, help="Chunk duration (e.g. 20m, 1200s, 00:20:00.000)")
    p_split.add_argument("-o", "--output", help="Output filename prefix")
    p_split.add_argument("--keep-absolute", action="store_true", help="Do not reset timestamps to 0 in split parts")
    p_split.add_argument("--encoding", help="File encoding")
    p_split.set_defaults(func=cmd_split)

    # join
    p_join = subparsers.add_parser("join", help="Concatenate multiple subtitle files into one")
    p_join.add_argument("inputs", nargs="+", help="Subtitle files to concatenate")
    p_join.add_argument("-o", "--output", required=True, help="Output subtitle file path")
    p_join.add_argument("--gap", default="0ms", type=_timestamp, help="Gap between consecutive files (e.g. 1000ms)")
    p_join.add_argument("--no-shift", action="store_true", help="Do not shift subsequent files after preceding ends")
    p_join.add_argument("--encoding", help="File encoding")
    p_join.set_defaults(func=cmd_join)

    # renumber
    p_renum = subparsers.add_parser("renumber", help="Renumber cues sequentially")
    p_renum.add_argument("input", help="Input subtitle file")
    p_renum.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p_renum.add_argument("-i", "--in-place", action="store_true", help="Modify input file in place")
    p_renum.add_argument("--start", type=int, default=1, help="Starting cue index (default: 1)")
    p_renum.add_argument("--encoding", help="File encoding")
    p_renum.set_defaults(func=cmd_renumber)

    # strip-tags
    p_strip = subparsers.add_parser("strip-tags", help="Remove styling and formatting tags from cues")
    p_strip.add_argument("input", help="Input subtitle file")
    p_strip.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p_strip.add_argument("-i", "--in-place", action="store_true", help="Modify input file in place")
    p_strip.add_argument("--encoding", help="File encoding")
    p_strip.set_defaults(func=cmd_strip_tags)

    # lint
    p_lint = subparsers.add_parser("lint", help="Lint subtitle files for timing, formatting, and encoding errors")
    p_lint.add_argument("files", nargs="+", help="Subtitle files or glob patterns (e.g. *.srt)")
    p_lint.add_argument("--fix", action="store_true", help="Automatically repair safe issues")
    p_lint.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")
    p_lint.add_argument("--strict", action="store_true", help="Treat warnings as errors for exit code")
    p_lint.add_argument("--max-cps", type=float, default=17.0, help="Maximum characters per second (default: 17)")
    p_lint.add_argument("--max-line-length", type=int, default=42, help="Maximum characters per line (default: 42)")
    p_lint.add_argument("--max-lines", type=int, default=2, help="Maximum lines per cue (default: 2)")
    p_lint.add_argument("--min-duration", type=int, default=500, help="Minimum cue duration in ms (default: 500)")
    p_lint.add_argument("--max-duration", type=int, default=7000, help="Maximum cue duration in ms (default: 7000)")
    p_lint.add_argument("--encoding", help="File encoding")
    p_lint.set_defaults(func=cmd_lint)

    # info
    p_info = subparsers.add_parser("info", help="Inspect subtitle file statistics and encoding")
    p_info.add_argument("files", nargs="+", help="Subtitle files or glob patterns")
    p_info.add_argument("--encoding", help="File encoding")
    p_info.set_defaults(func=cmd_info)

    # transcribe (optional extra; faster-whisper is imported lazily)
    add_transcribe_parser(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scale":
        if args.factor is not None and args.to_fps is not None:
            args.command_parser.error("--factor cannot be combined with --to-fps")
        if args.from_fps is not None and args.to_fps is None:
            args.command_parser.error("--from-fps requires --to-fps")
    try:
        return args.func(args)
    except (ValueError, OSError, LookupError) as exc:
        message = " ".join(str(exc).splitlines())
        sys.stderr.write(f"subtool {args.command}: error: {message}\n")
        return 2 if isinstance(exc, _UsageError) else 1


if __name__ == "__main__":
    sys.exit(main())
