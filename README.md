# subtitle-tools

A zero-dependency Python CLI and library to convert, transform, fix, and lint subtitle files across SubRip (`.srt`), WebVTT (`.vtt`), and Advanced SubStation Alpha (`.ass` / `.ssa`).

## Overview

Content creators, video editors, and translators frequently need to shift, scale, merge, split, and clean subtitle files across varying platforms. Existing software is either GUI-only, unmaintained, or bloated with heavy C/FFmpeg dependencies.

`subtitle-tools` provides a clean, modern, zero-runtime-dependency CLI (`subtool`) and typed Python library (`src/` layout, `py.typed`) to manipulate subtitles with high precision.

## Key Features

- **Zero runtime dependencies**: Pure standard library Python >= 3.10.
- **Multi-format support**:
  - **SubRip (`.srt`)**: Robust timestamp and index parsing, tolerant of common syntax defects.
  - **WebVTT (`.vtt`)**: Preserves cue identifiers, cue settings, `NOTE` blocks, `STYLE` blocks, and `REGION` definitions.
  - **ASS / SSA (`.ass`, `.ssa`)**: Handles `[Script Info]`, `[V4+ Styles]`, and `[Events]` while keeping unknown sections (`[Aegisub Project Garbage]`, fonts, graphics) verbatim.
- **Operations**:
  - `convert`: Format conversion between SRT, WebVTT, and ASS.
  - `shift`: Shift timestamps by positive/negative offsets (`1500ms`, `-2s`) or align to target timestamps.
  - `scale`: Frame rate conversion (e.g., 23.976 to 25 fps PAL speedup) or arbitrary multipliers.
  - `merge`: Stack two subtitle files into dual-language cues (primary on top, secondary on bottom).
  - `split`: Partition subtitle files into duration-based segments (e.g., 20-minute chunks).
  - `join`: Concatenate multiple subtitle files sequentially with optional gaps.
  - `renumber`: Re-index cues sequentially from 1.
  - `strip-tags`: Remove HTML, WebVTT, and ASS formatting tags and decode HTML entities.
- **Comprehensive Linting & Auto-Fix**:
  - Evaluates timing, reading speed, cue length, and formatting syntax against configurable thresholds.
  - Automatic repair (`--fix`) for safe rules: resolves slight overlaps, fixes zero/negative durations, strips empty cues, and closes unclosed formatting tags.
- **Documented Legacy Encoding Detection**:
  - Automatic detection order: `utf-8-sig` -> `utf-8` -> `cp1252` -> `cp1254` -> `latin-1`.

## Installation

Install using pip:

```bash
pip install .
```

For development and running tests:

```bash
pip install -e ".[dev]"
```

## CLI Reference (`subtool`)

### Convert formats
```bash
# Convert between formats by file extension
subtool convert input.srt output.vtt
subtool convert input.vtt output.ass

# Explicit format specification
subtool convert input.txt output.vtt --from-format srt --to-format vtt
```

### Shift timing
```bash
# Shift forward by 1500 milliseconds
subtool shift input.srt -o shifted.srt --by 1500ms

# Shift backward by 2 seconds
subtool shift input.srt -o shifted.srt --by -2s

# Align the first cue to start at exactly 00:01:00.000
subtool shift input.srt -o shifted.srt --to 00:01:00.000

# Overwrite file in place
subtool shift input.srt --in-place --by 500ms
```

### Scale framerate / timing
```bash
# Convert from 23.976 fps to 25 fps (PAL speedup)
subtool scale input.srt -o scaled.srt --from-fps 23.976 --to-fps 25

# Convert from 25 fps to 23.976 fps
subtool scale input.srt -o scaled.srt --from-fps 25 --to-fps 23.976

# Direct timing multiplier
subtool scale input.srt -o scaled.srt --factor 1.05
```

### Merge dual-language subtitles
```bash
# Merge English and Turkish subtitles into stacked dual cues
subtool merge english.srt turkish.srt -o dual.srt

# Custom line separator
subtool merge english.srt turkish.srt -o dual.srt --separator " | "
```

### Split subtitles by duration
```bash
# Split into 20-minute chunks
subtool split input.srt --duration 20m -o part

# Split every 1200 seconds
subtool split input.srt --duration 1200s
```

### Join multiple files
```bash
# Concatenate files with a 1-second gap
subtool join part1.srt part2.srt part3.srt -o full.srt --gap 1000ms
```

### Renumber cues
```bash
subtool renumber input.srt -o renumbered.srt --start 1
```

### Strip formatting tags
```bash
# Remove <i>, <b>, <font>, and ASS override tags
subtool strip-tags input.srt -o clean.srt
```

### Lint and auto-fix
```bash
# Lint files and output human-readable report
subtool lint *.srt

# Output machine-readable JSON report
subtool lint *.srt --format json

# Auto-repair fixable issues in place
subtool lint *.srt --fix

# Configure linting thresholds
subtool lint *.srt --max-cps 18 --max-line-length 40 --max-lines 2 --min-duration 400
```

### Inspect subtitle file metadata
```bash
subtool info *.srt *.vtt *.ass
```

## Linting Rules

| Rule ID | Severity | Description | Fixable via `--fix` |
| ------- | -------- | ----------- | ------------------- |
| `overlap` | Error | Cue starts before the previous cue ends. | Yes (if overlap <= 1500ms) |
| `negative-duration` | Error | Cue end timestamp is before its start timestamp. | Yes (swapped or adjusted) |
| `zero-duration` | Error | Cue end timestamp equals its start timestamp. | Yes (set to min duration) |
| `too-short-duration` | Warning | Cue duration is shorter than minimum (default: 500ms). | No |
| `too-long-duration` | Warning | Cue duration exceeds maximum (default: 7000ms). | No |
| `cps-limit` | Warning | Characters per second exceeds reading limit (default: 17 cps). | No |
| `line-length` | Warning | Single line exceeds maximum character length (default: 42 chars). | No |
| `line-count` | Warning | Cue has more lines than permitted (default: 2 lines). | No |
| `empty-cue` | Error | Cue contains no visible text (whitespace or tags only). | Yes (removed) |
| `unbalanced-tags` | Error | Unclosed or mismatched HTML/VTT or ASS styling tags. | Yes (closed or stripped) |
| `encoding-issue` | Warning | UTF-8 Byte Order Mark (BOM) or mixed CRLF/LF line endings. | Yes (normalized) |

## Encoding Detection Order

When reading subtitle files without an explicit `--encoding` argument, `subtitle-tools` applies the following fallback sequence:

1. **`utf-8-sig`**: Checks for the 3-byte UTF-8 BOM (`0xEF, 0xBB, 0xBF`).
2. **`utf-8`**: Strict UTF-8 decoding.
3. **`cp1254` / `cp1252`**: If non-UTF-8 bytes contain Windows-1254 characteristic Turkish characters (`ş`, `ğ`, `ı`, `Ş`, `Ğ`, `İ`), `cp1254` is applied. Otherwise, Windows-1252 (Western European ANSI) is used.
4. **`cp1254`**: Fallback attempt for Windows Turkish ANSI if CP1252 fails on undefined byte ranges.
5. **`latin-1`**: ISO-8859-1 fallback that maps all single-byte values (0x00 to 0xFF) safely without decoding errors.

## Python Library API

```python
from subtitle_tools import parse, write, shift, merge, lint_document, LintConfig

# Parse subtitle text
with open("input.srt", "r", encoding="utf-8") as f:
    doc = parse(f.read(), fmt="srt")

# Shift cues forward by 1.5 seconds
shifted_doc = shift(doc, by_ms=1500)

# Lint document
config = LintConfig(max_cps=17.0, max_line_length=42)
issues = lint_document(shifted_doc, config=config)

for issue in issues:
    print(f"[{issue.severity.upper()}] {issue.rule_id}: {issue.message}")

# Serialize to WebVTT
vtt_text = write(shifted_doc, fmt="vtt")
```

## Running Tests

Tests can be executed using standard library `unittest` (requiring zero third-party dependencies):

```bash
python -m unittest discover -s tests
```

Or using `pytest`:

```bash
pytest
```

## Contributing

Please review [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and development workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Yusuf Berat Zengin.
