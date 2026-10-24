"""``subtool transcribe``: offline, word-timed subtitles from local media.

There is no network or model download option. faster-whisper is imported only when
a media file is actually transcribed; ``--words-json`` never loads it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from subtitle_tools import __version__

from . import writers
from .burn import burn
from .engine import transcribe
from .layout import LayoutConfig, layout, layout_warnings
from .models import Word
from .style import Style, load_style


def add_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register the ``transcribe`` subcommand on the main ``subtool`` parser."""
    result: argparse.ArgumentParser = subparsers.add_parser(
        "transcribe",
        help="Create offline, word-timed subtitles from local media (extra: transcribe)",
        description=(
            "Create offline, word-timed subtitles from local media. Needs "
            "pip install 'subtitle-tools[transcribe]' unless --words-json is used."
        ),
    )
    result.add_argument(
        "input",
        nargs="?",
        default=None,
        type=Path,
        help="Input media file (optional if --words-json is provided)",
    )
    result.add_argument(
        "-o", "--output", type=Path, help="Output filename or stem (default: input stem)"
    )
    result.add_argument("--format", choices=("srt", "vtt", "ass", "all"), default="srt")
    result.add_argument(
        "--model", default="small", help="Cached model name or local model directory"
    )
    result.add_argument("--mode", choices=("words", "groups"), default="groups")
    result.add_argument("--max-chars", type=int, default=18)
    result.add_argument("--max-lines", type=int, default=2)
    result.add_argument("--pause-threshold", type=float, default=0.6)
    result.add_argument("--min-duration", type=float, default=0.8)
    result.add_argument("--max-cps", type=float, default=18.0)
    result.add_argument("--upper", action="store_true")
    result.add_argument("--burn", action="store_true", help="Also create <stem>.burned.mp4")
    result.add_argument("--lang", default="tr")
    result.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    result.add_argument("--compute-type", default=None)
    result.add_argument("--no-vad", action="store_true")
    result.add_argument("--style", type=Path, help="ASS style JSON or YAML")
    result.add_argument("--position", choices=("bottom", "middle", "upper"))
    result.add_argument("--report", choices=("json",), help="Write <stem>.report.json")
    result.add_argument("--confidence", type=float, default=0.6)
    result.add_argument(
        "--words-json",
        type=Path,
        help="Input pre-saved word list JSON without loading faster-whisper",
    )
    result.add_argument(
        "--save-words",
        type=Path,
        help="Save recognized words to JSON array for later re-layout",
    )
    result.set_defaults(func=cmd_transcribe, command_parser=result)
    return result


def _load_words_json(path: Path) -> tuple[Word, ...]:
    if not path.is_file():
        raise ValueError("Words JSON file must exist.")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        raise ValueError(f"Failed to read words JSON file: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("Words JSON must be an array of word objects.")  # noqa: TRY004 -- user input
    words: list[Word] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each item in words JSON must be an object.")  # noqa: TRY004 -- user input
        try:
            if not isinstance(item.get("text"), str):
                raise TypeError("text must be a string")
            words.append(
                Word(
                    start=float(item["start"]),
                    end=float(item["end"]),
                    text=str(item["text"]),
                    prob=float(item.get("prob", 1.0)),
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid word entry in words JSON: {exc}") from exc
    return tuple(words)


def cmd_transcribe(args: argparse.Namespace) -> int:
    if not args.input and not args.words_json:
        args.command_parser.error("the following arguments are required: input (or --words-json)")
    try:
        return _run(args)
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        message = " ".join(str(exc).splitlines())
        sys.stderr.write(f"subtool transcribe: error: {message}\n")
        return 1


def _run(args: argparse.Namespace) -> int:
    if args.input:
        if not args.input.is_file():
            raise ValueError("Input must be an existing local media file.")
        try:
            if args.input.stat().st_size == 0:
                raise ValueError(f"Input media file '{args.input}' is empty.")
        except (FileNotFoundError, OSError):
            pass
    if args.words_json and not args.words_json.is_file():
        raise ValueError("Words JSON file must exist.")
    if args.burn and not args.input:
        raise ValueError("--burn requires an input media file.")
    config = LayoutConfig(
        max_chars=args.max_chars,
        max_lines=args.max_lines,
        pause_threshold=args.pause_threshold,
        min_duration=args.min_duration,
        max_cps=args.max_cps,
        mode=args.mode,
        upper=args.upper,
        # Dotted/dotless I mapping is wrong outside Turkic languages.
        turkish_case=args.lang.strip().lower().split("-")[0] in ("tr", "az"),
    )
    if not 0 <= args.confidence <= 1:
        raise ValueError("Confidence threshold must be between 0 and 1.")
    style = load_style(args.style) if args.style else Style()
    if args.position:
        style = replace(style, position=args.position)
    target = args.output or (
        args.input.with_suffix("") if args.input else args.words_json.with_suffix("")
    )
    stem = (
        target.with_suffix("")
        if target.suffix.lower() in (".srt", ".vtt", ".ass", ".json")
        else target
    )
    formats: tuple[str, ...] = ("srt", "vtt", "ass") if args.format == "all" else (args.format,)
    if args.burn and "ass" not in formats:
        formats += ("ass",)
    outputs = {fmt: Path(str(stem) + "." + fmt) for fmt in formats}
    report_path = Path(str(stem) + ".report.json")
    burned_path = Path(str(stem) + ".burned.mp4")
    planned = list(outputs.values())
    if args.report:
        planned.append(report_path)
    if args.burn:
        planned.append(burned_path)
    if args.save_words:
        planned.append(args.save_words)
    protected: set[Path] = set()
    for source in (args.input, args.style, args.words_json):
        if source:
            protected.add(source.resolve())
    if any(p.exists() or p.resolve() in protected for p in planned):
        raise ValueError("Output files must be new and distinct from input and style files.")
    if args.words_json:
        words = _load_words_json(args.words_json)
        duration = words[-1].end if words else 0.0
        language = args.lang
        device = "none"
        compute_type = "none"
    else:
        transcript = transcribe(
            args.input,
            model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            language=args.lang,
            vad=not args.no_vad,
        )
        words = transcript.words
        duration = transcript.duration
        language = transcript.language
        device = transcript.device
        compute_type = transcript.compute_type
    if args.save_words:
        args.save_words.parent.mkdir(parents=True, exist_ok=True)
        with args.save_words.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump([asdict(w) for w in words], handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    cues = layout(words, config, duration=duration)
    warnings = layout_warnings(cues, config)
    for fmt, path in outputs.items():
        text = (
            writers.ass(cues, style=style, karaoke=args.mode == "words")
            if fmt == "ass"
            else writers.srt(cues)
            if fmt == "srt"
            else writers.vtt(cues)
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    if args.report:
        report = {
            "version": __version__,
            "language": language,
            "duration": duration,
            "device": device,
            "compute_type": compute_type,
            "cue_count": len(cues),
            "confidence_threshold": args.confidence,
            "low_confidence_words": [asdict(w) for w in words if w.prob < args.confidence],
            "layout_warnings": warnings,
        }
        with report_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    if args.burn:
        burn(args.input, outputs["ass"], burned_path)
    print(f"Created {len(cues)} subtitle cues.")
    if warnings:
        print(
            f"Warning: {len(warnings)} cues exceed layout targets; use --report json.",
            file=sys.stderr,
        )
    return 0
