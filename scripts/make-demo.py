"""Generate docs/demo.svg by running real CLI commands on sample subtitles."""

from __future__ import annotations

import html
import io
import re
import shutil
from pathlib import Path
from unittest.mock import patch

from subtitle_tools.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
TMP_DIR = REPO_ROOT / "is" / "tmp" / "demo_gen"


def run_cli_command(args: list[str], cwd: Path) -> str:
    """Run subtool CLI command in cwd and capture combined stdout/stderr."""
    import os

    old_cwd = os.getcwd()
    os.chdir(cwd)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    try:
        with (
            patch("sys.stdout.write", stdout_buf.write),
            patch("sys.stderr.write", stderr_buf.write),
        ):
            main(args)
    finally:
        os.chdir(old_cwd)

    return stdout_buf.getvalue() + stderr_buf.getvalue()


def colorize_line(line: str) -> str:
    """Convert a terminal output line into SVG tspan elements with terminal colors."""
    escaped = html.escape(line)

    # Prompt line ($ subtool ...)
    if line.startswith("$ "):
        parts = escaped.split(" ", 2)
        prompt = f'<tspan fill="#a6e3a1" font-weight="600">{parts[0]}</tspan>'
        cmd = f' <tspan fill="#f5c2e7" font-weight="600">{parts[1]}</tspan>'
        rest = f' <tspan fill="#89dceb">{parts[2]}</tspan>' if len(parts) > 2 else ""
        return f"{prompt}{cmd}{rest}"

    # File header (e.g. movie.srt:)
    if re.match(r"^[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+:", line):
        return f'<tspan fill="#cdd6f4" font-weight="700">{escaped}</tspan>'

    # Fix summary (Fixed X issue(s) automatically)
    if "Fixed" in line and "automatically" in line:
        return f'<tspan fill="#a6e3a1" font-weight="600">{escaped}</tspan>'

    # Linter issues: [ERROR] or [WARNING]
    lint_match = re.match(
        r"^(\s+)(\[(?:ERROR|WARNING)\])\s+([a-zA-Z0-9_\-]+)(\s+\[Cue\s+#[0-9]+\])?:(.*)$",
        line,
    )
    if lint_match:
        indent = html.escape(lint_match.group(1))
        sev = lint_match.group(2)
        rule = html.escape(lint_match.group(3))
        cue = html.escape(lint_match.group(4) or "")
        msg = html.escape(lint_match.group(5))

        sev_color = "#f38ba8" if "ERROR" in sev else "#f9e2af"
        sev_span = f'<tspan fill="{sev_color}" font-weight="700">{sev}</tspan>'
        rule_span = f'<tspan fill="#89b4fa" font-weight="600">{rule}</tspan>'
        cue_span = f'<tspan fill="#6c7086">{cue}</tspan>' if cue else ""
        msg_span = f'<tspan fill="#bac2de">:{msg}</tspan>'
        return f"{indent}{sev_span} {rule_span}{cue_span}{msg_span}"

    # Info lines: Format:, Encoding:, Cues:, Duration:
    info_match = re.match(r"^(\s+)([A-Za-z]+:)(\s+)(.*)$", line)
    if info_match:
        indent = html.escape(info_match.group(1))
        label = html.escape(info_match.group(2))
        spacing = html.escape(info_match.group(3))
        val = html.escape(info_match.group(4))
        return (
            f'{indent}<tspan fill="#89b4fa" font-weight="600">{label}</tspan>'
            f'{spacing}<tspan fill="#cdd6f4">{val}</tspan>'
        )

    # Default fallback
    return f'<tspan fill="#bac2de">{escaped}</tspan>'


def generate_svg(terminal_lines: list[str]) -> str:
    """Generate SVG document enclosing the terminal lines."""
    line_height = 22
    pad_top = 58
    pad_left = 24
    height = pad_top + (len(terminal_lines) * line_height) + 20
    width = 780

    svg_lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" font-family="ui-monospace, \'Cascadia Code\', '
            f'\'SF Mono\', Consolas, \'Liberation Mono\', Menlo, monospace" font-size="13">'
        ),
        '  <defs>',
        '    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">',
        '      <stop offset="0%" stop-color="#181825"/>',
        '      <stop offset="100%" stop-color="#1e1e2e"/>',
        '    </linearGradient>',
        '    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">',
        '      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.45"/>',
        '    </filter>',
        '  </defs>',
        f'  <rect width="{width}" height="{height}" rx="10" fill="#181825" stroke="#313244" stroke-width="1" filter="url(#shadow)"/>',
        f'  <path d="M0 10C0 4.477 4.477 0 10 0h{width - 20}c5.523 0 10 4.477 10 10v28H0V10z" fill="url(#headerGrad)"/>',
        '  <line x1="0" y1="38" x2="' + str(width) + '" y2="38" stroke="#313244" stroke-width="1"/>',
        '  <!-- Window Controls -->',
        '  <circle cx="24" cy="19" r="6" fill="#f38ba8"/>',
        '  <circle cx="44" cy="19" r="6" fill="#f9e2af"/>',
        '  <circle cx="64" cy="19" r="6" fill="#a6e3a1"/>',
        f'  <text x="{width // 2}" y="23" fill="#6c7086" font-size="12" font-weight="500" text-anchor="middle">subtool — terminal</text>',
        '  <!-- Terminal Output -->',
    ]

    for idx, raw_line in enumerate(terminal_lines):
        y_pos = pad_top + (idx * line_height)
        content = colorize_line(raw_line) if raw_line else ""
        svg_lines.append(
            f'  <text x="{pad_left}" y="{y_pos}" xml:space="preserve">{content}</text>'
        )

    svg_lines.append("</svg>\n")
    return "\n".join(svg_lines)


def main_gen() -> None:
    """Capture real CLI output and write docs/demo.svg."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    sample_src = REPO_ROOT / "tests" / "fixtures" / "malformed.srt"
    demo_file = TMP_DIR / "movie.srt"
    shutil.copyfile(sample_src, demo_file)

    terminal_lines: list[str] = []

    # 1. Run subtool lint movie.srt
    terminal_lines.append("$ subtool lint movie.srt")
    out1 = run_cli_command(["lint", "movie.srt"], cwd=TMP_DIR)
    for line in out1.strip().splitlines():
        if line.strip():
            terminal_lines.append(line)

    terminal_lines.append("")

    # 2. Run subtool lint movie.srt --fix
    terminal_lines.append("$ subtool lint movie.srt --fix")
    out2 = run_cli_command(["lint", "movie.srt", "--fix"], cwd=TMP_DIR)
    for line in out2.strip().splitlines():
        if line.strip():
            terminal_lines.append(line)

    terminal_lines.append("")

    # 3. Run subtool info movie.srt
    terminal_lines.append("$ subtool info movie.srt")
    out3 = run_cli_command(["info", "movie.srt"], cwd=TMP_DIR)
    for line in out3.strip().splitlines():
        if line.strip():
            terminal_lines.append(line)

    svg_content = generate_svg(terminal_lines)
    output_path = DOCS_DIR / "demo.svg"
    output_path.write_text(svg_content, encoding="utf-8")
    print(f"Generated {output_path} with {len(terminal_lines)} lines")


if __name__ == "__main__":
    main_gen()
