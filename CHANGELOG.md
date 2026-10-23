# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
