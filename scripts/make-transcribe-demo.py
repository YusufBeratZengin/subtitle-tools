"""Generate docs/transcribe-demo.svg from a real `subtool transcribe` run (no model needed)."""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ARGS = [
    "--words-json",
    "examples/transcribe/sample.words.json",
    "-o",
    "captions",
    "--format",
    "all",
    "--mode",
    "words",
    "--upper",
]


def capture_demo_output() -> list[str]:
    """Run the documented command and read its generated SRT, without a model."""
    work_dir = ROOT / "is"
    work_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="demo-", dir=work_dir) as tmp:
        workspace = Path(tmp)
        fixture = workspace / "examples/transcribe/sample.words.json"
        fixture.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "examples/transcribe/sample.words.json", fixture)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["HF_HUB_OFFLINE"] = "1"
        env["HF_HUB_DISABLE_TELEMETRY"] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "subtitle_tools", "transcribe", *DEMO_ARGS],
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            check=True,
        )
        srt = (workspace / "captions.srt").read_text(encoding="utf-8")
        excerpt = "\n\n".join(srt.strip().split("\n\n")[:3])
        return [
            "$ subtool transcribe " + " ".join(DEMO_ARGS),
            *result.stdout.strip().splitlines(),
            "",
            "# captions.srt (first 3 cues)",
            *excerpt.splitlines(),
        ]


def build_svg(lines: list[str]) -> str:
    """Render terminal lines into an SVG with dark background, rounded window, and 3 dots."""
    width = max(820, 48 + max(len(line) for line in lines) * 8)
    header_height = 40
    padding_x = 24
    padding_top = 68
    line_height = 20
    font_size = 13

    # Total height: header + content + bottom padding
    total_lines = len(lines)
    height = padding_top + (total_lines * line_height) + 16

    content_spans: list[str] = []

    for i, line in enumerate(lines):
        y = padding_top + (i * line_height)
        if not line.strip():
            continue

        escaped = html.escape(line)

        if line.startswith("$ "):
            styled = f'<tspan fill="#3fb950" font-weight="bold">{escaped}</tspan>'
        elif line.startswith("# "):
            styled = f'<tspan fill="#8b949e">{escaped}</tspan>'
        elif " --> " in line:
            styled = f'<tspan fill="#79c0ff">{escaped}</tspan>'
        else:
            styled = f'<tspan fill="#c9d1d9">{escaped}</tspan>'

        content_spans.append(f'  <text x="{padding_x}" y="{y}">{styled}</text>')

    body_content = "\n".join(content_spans)
    title_font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    mono_font = "ui-monospace, 'SF Mono', 'Cascadia Code', 'Fira Code', Menlo, Consolas, monospace"

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-label="subtool transcribe: real CLI output and generated SRT cues">\n'
        f"  <defs>\n"
        f'    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">\n'
        f'      <feDropShadow dx="0" dy="6" stdDeviation="12" '
        f'flood-color="#000000" flood-opacity="0.4"/>\n'
        f"    </filter>\n"
        f"  </defs>\n\n"
        f"  <!-- Terminal Window Background -->\n"
        f'  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" ry="10" '
        f'fill="#0d1117" stroke="#30363d" stroke-width="1.2" filter="url(#shadow)"/>\n\n'
        f"  <!-- Window Header / Title Bar -->\n"
        f'  <path d="M 1 11 A 10 10 0 0 1 11 1 L {width - 11} 1 A 10 10 0 0 1 {width - 1} 11 '
        f'L {width - 1} {header_height} L 1 {header_height} Z" fill="#161b22"/>\n'
        f'  <line x1="1" y1="{header_height}" x2="{width - 1}" y2="{header_height}" '
        f'stroke="#30363d" stroke-width="1"/>\n\n'
        f"  <!-- Window Controls (3 dots: Red, Yellow, Green) -->\n"
        f'  <circle cx="20" cy="20" r="5.5" fill="#ff5f56" stroke="#e0443e" '
        f'stroke-width="0.5"/>\n'
        f'  <circle cx="38" cy="20" r="5.5" fill="#ffbd2e" stroke="#dea123" '
        f'stroke-width="0.5"/>\n'
        f'  <circle cx="56" cy="20" r="5.5" fill="#27c93f" stroke="#1aab29" '
        f'stroke-width="0.5"/>\n\n'
        f"  <!-- Centered Window Title -->\n"
        f'  <text x="{width // 2}" y="24" text-anchor="middle" fill="#8b949e" '
        f'font-family="{title_font}" font-size="12" font-weight="500">'
        f"subtool transcribe — terminal</text>\n\n"
        f"  <!-- Monospace Terminal Lines -->\n"
        f'  <g font-family="{mono_font}" font-size="{font_size}" xml:space="preserve">\n'
        f"{body_content}\n"
        f"  </g>\n"
        f"</svg>\n"
    )
    return svg


def main() -> int:
    dest = ROOT / "docs/transcribe-demo.svg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = capture_demo_output()
    svg = build_svg(lines)
    dest.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Generated {dest.relative_to(ROOT)} ({len(lines)} terminal lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
