"""Generate deterministic `subtool transcribe` samples and report for documentation.

Run from the repository root: python scripts/make_transcribe_examples.py
"""

import json
from dataclasses import asdict
from pathlib import Path

from subtitle_tools import __version__
from subtitle_tools.transcribe import LayoutConfig, Word, layout, layout_warnings
from subtitle_tools.transcribe.writers import ass, srt, vtt

SAMPLE_WORDS: tuple[Word, ...] = (
    Word(0.00, 0.42, "Bugün", 0.98),
    Word(0.48, 0.95, "dikey", 0.97),
    Word(1.02, 1.60, "videolar", 0.95),
    Word(1.68, 2.05, "için", 0.99),
    Word(2.12, 2.75, "altyazı", 0.96),
    Word(2.82, 3.55, "hazırlıyoruz", 0.94),
    Word(3.68, 4.10, "çünkü", 0.55),
    Word(4.18, 4.52, "iyi", 0.99),
    Word(4.58, 4.95, "ışık", 0.97),
    Word(5.02, 5.25, "ve", 0.96),
    Word(5.30, 5.62, "net", 0.98),
    Word(5.68, 6.05, "ses", 0.99),
    Word(6.12, 6.45, "çok", 0.95),
    Word(6.50, 7.10, "önemli.", 0.98),
)


def generate(target_dir: Path | str = "examples/transcribe") -> None:
    dest = Path(target_dir)
    dest.mkdir(parents=True, exist_ok=True)

    config = LayoutConfig(mode="words", upper=True, turkish_case=True)
    cues = layout(SAMPLE_WORDS, config, duration=7.20)

    srt_content = srt(cues)
    vtt_content = vtt(cues)
    ass_content = ass(cues, karaoke=True)

    (dest / "sample.srt").write_text(srt_content, encoding="utf-8", newline="\n")
    (dest / "sample.vtt").write_text(vtt_content, encoding="utf-8", newline="\n")
    (dest / "sample.ass").write_text(ass_content, encoding="utf-8", newline="\n")
    (dest / "sample.words.json").write_text(
        json.dumps([asdict(w) for w in SAMPLE_WORDS], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    report = {
        "version": __version__,
        "language": "tr",
        "duration": 7.20,
        "device": "cpu",
        "compute_type": "int8",
        "cue_count": len(cues),
        "confidence_threshold": 0.6,
        "low_confidence_words": [asdict(w) for w in SAMPLE_WORDS if w.prob < 0.6],
        "layout_warnings": layout_warnings(cues, config),
    }
    (dest / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    import sys

    output = sys.argv[1] if len(sys.argv) > 1 else "examples/transcribe"
    generate(output)
    print(f"Generated sample files in {output}")
