# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-24

### Added
- `subtool transcribe`: offline, word-timed subtitles for short vertical videos, merged in from the former `altyazi-tr` project. Install with `pip install "subtitle-tools[transcribe]"`.
  - Local faster-whisper recognition that never downloads a model (`local_files_only=True`), with CUDA auto-detection and CPU `int8` fallback.
  - Pause-aware layout for 9:16 video: line and cue limits, reading-speed targets, Turkish uppercase (`i→İ`, `ı→I`), and no stranded conjunctions at line ends.
  - Karaoke ASS with active-word highlighting, JSON/YAML ASS styles, and `--burn` through local ffmpeg.
  - `--words-json` / `--save-words` to re-layout saved word timings without loading the model, and `--report json` with low-confidence words and layout warnings.
- New optional extras: `transcribe` (faster-whisper), `ffmpeg` (imageio-ffmpeg for `--burn`), and `yaml` (PyYAML for YAML styles). The core package still has zero runtime dependencies; faster-whisper is imported lazily.
- `subtitle_tools.transcribe` Python API (`Word`, `WordCue`, `LayoutConfig`, `layout`, `layout_warnings`, `to_document`, `transcribe`, `Style`, `load_style`).
- Top-level `subtool --version`.
- `docs/transcribe.md`, `examples/transcribe/`, and a generated `docs/transcribe-demo.svg` (`scripts/make-transcribe-demo.py`).
- Optional pre-commit credential guard (`.githooks/pre-commit`, `scripts/check_secrets.py`).

### Changed
- Transcription output reuses the core `Cue`, `SubtitleDocument`, `AssStyle`, and SRT/WebVTT/ASS writers instead of separate serializers. Compared with `altyazi-tr`, SRT and WebVTT files end with a single newline.
- CI tests Python 3.10, 3.11, 3.12, and 3.13, runs the `unittest` suite against a core-only install, and declares read-only permissions.
- `ruff` and `mypy` are part of the `dev` extra.

## [0.1.0] - 2026-10-23

### Added
- Core subtitle data models (`Cue`, `SubtitleDocument`, `AssStyle`) with typed attributes.
- Parser and writer for SubRip (`.srt`) format with tolerant timestamp and index parsing.
- Parser and writer for WebVTT (`.vtt`) format supporting cue identifiers, settings, NOTE blocks, and STYLE blocks.
- Parser and writer for Advanced SubStation Alpha (`.ass` / `.ssa`) format with support for `[Script Info]`, `[V4+ Styles]`, `[Events]`, and verbatim preservation of unknown sections.
- Encoding detection engine for legacy files supporting `utf-8-sig`, `utf-8`, `cp1252`, `cp1254`, and `latin-1` fallback order.
- Format conversion between SRT, WebVTT, and ASS.
- Subtitle operations:
  - `shift`: Time shifting by positive/negative milliseconds, seconds, timestamp string, or first-cue alignment.
  - `scale`: Frame rate conversion (e.g., 23.976 to 25 fps, 25 to 23.976, or custom multipliers).
  - `merge`: Merge two language files into stacked cues (primary and secondary languages).
  - `split`: Split subtitle documents by duration intervals into multiple parts.
  - `join`: Concatenate multiple subtitle files sequentially with optional gaps.
  - `renumber`: Re-index cues sequentially from 1.
  - `strip-tags`: Remove HTML, WebVTT, and ASS styling tags and unescape HTML entities.
- Linting system with rule identifiers:
  - `overlap`: Detect cues that start before previous cues end.
  - `negative-duration`: Detect cues whose end time is before start time.
  - `zero-duration`: Detect cues whose end time equals start time.
  - `too-short-duration`: Detect cues shorter than configured minimum (default: 500ms).
  - `too-long-duration`: Detect cues longer than configured maximum (default: 7000ms).
  - `cps-limit`: Detect reading speed exceeding characters-per-second limit (default: 17 cps).
  - `line-length`: Detect individual lines exceeding character count (default: 42 chars).
  - `line-count`: Detect cues with more lines than configured maximum (default: 2 lines).
  - `empty-cue`: Detect cues containing no text or whitespace only.
  - `unbalanced-tags`: Detect unclosed or mismatched HTML/formatting tags.
  - `encoding-issue`: Detect UTF-8 BOM, invalid byte sequences, or mixed CRLF/LF newlines.
- Auto-fixing engine (`--fix`) for safe rules:
  - Removal of empty cues.
  - Closing or cleaning unbalanced tags.
  - Normalizing CRLF/LF newlines and stripping UTF-8 BOM.
  - Resolving slight overlaps within tolerance.
  - Repairing zero or negative durations.
  - Re-indexing cues.
- `subtool` CLI supporting subcommands: `convert`, `shift`, `scale`, `merge`, `split`, `join`, `renumber`, `strip-tags`, `lint`, and `info`.
- Support for JSON output (`--format json`) in the linting CLI.
- Standard library unit tests and pytest compatibility.
