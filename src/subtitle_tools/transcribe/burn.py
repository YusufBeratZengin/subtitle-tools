"""Optional local ffmpeg execution; media and subtitles are never uploaded."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def find_ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        executable = str(get_ffmpeg_exe())
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError("ffmpeg was not found. Install ffmpeg or pip install 'subtitle-tools[ffmpeg]'.") from exc
    if not Path(executable).is_file():
        raise RuntimeError("The imageio-ffmpeg executable does not exist.")
    return executable


def burn(source: Path, subtitles: Path, output: Path) -> None:
    """Render with libass, H.264 video and AAC audio; refuse overwrites."""
    source, subtitles, output = (p.resolve() for p in (source, subtitles, output))
    if not source.is_file() or not subtitles.is_file():
        raise ValueError("Input media and subtitle files must exist.")
    if output.exists() or output in (source, subtitles):
        raise ValueError("Burn output must be a new file distinct from the inputs.")
    executable = find_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg's libass filter (-vf "ass=filename") parses arguments through a custom
    # filtergraph syntax where colons (:) delimit options, and backslashes (\), apostrophes ('),
    # and brackets act as escape/delimiter characters. On Windows, paths like
    # 'D:\Media Files\o\'clip\a.ass' contain drive letters with colons, backslashes, spaces,
    # and quotes which notoriously break filtergraph parsing if passed directly into the filter.
    # Copying subtitles into an isolated temporary folder as 'captions.ass' and running ffmpeg
    # with cwd=folder guarantees that ffmpeg only sees a simple relative filename, immune to
    # drive letters, apostrophes, spaces, and punctuation on both Windows and POSIX systems.
    with tempfile.TemporaryDirectory(prefix="subtitle-tools-") as folder:
        shutil.copyfile(subtitles, Path(folder) / "captions.ass")
        command = [
            executable,
            "-nostdin",
            "-n",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            "ass=captions.ass",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ]
        try:
            subprocess.run(command, cwd=folder, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            # ffmpeg can include media metadata in stderr; keep it local and terse.
            raise RuntimeError(
                "ffmpeg burn failed. Check for a video stream, libass, and libx264 support."
            ) from exc
