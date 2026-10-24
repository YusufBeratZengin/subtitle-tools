import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from scripts.make_transcribe_examples import SAMPLE_WORDS, generate
from subtitle_tools import __version__
from subtitle_tools.transcribe import LayoutConfig, layout
from subtitle_tools.transcribe.layout import layout_warnings

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "transcribe"


class ExamplesTests(unittest.TestCase):
    def test_deterministic_regeneration(self) -> None:
        examples_dir = EXAMPLES
        self.assertTrue(examples_dir.is_dir(), "examples/transcribe must exist.")

        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-examples-") as tmp:
            tmp_path = Path(tmp)
            generate(tmp_path)

            for filename in (
                "sample.srt",
                "sample.vtt",
                "sample.ass",
                "report.json",
                "sample.words.json",
            ):
                with self.subTest(file=filename):
                    expected = (examples_dir / filename).read_text(encoding="utf-8")
                    actual = (tmp_path / filename).read_text(encoding="utf-8")
                    self.assertEqual(actual, expected)

    def test_report_json_schema(self) -> None:
        report_path = EXAMPLES / "report.json"
        self.assertTrue(report_path.is_file(), "examples/transcribe/report.json must exist.")
        data = json.loads(report_path.read_text(encoding="utf-8"))

        expected_keys = {
            "version",
            "language",
            "duration",
            "device",
            "compute_type",
            "cue_count",
            "confidence_threshold",
            "low_confidence_words",
            "layout_warnings",
        }
        self.assertEqual(set(data.keys()), expected_keys)
        self.assertEqual(data["version"], __version__)
        self.assertIsInstance(data["language"], str)
        self.assertIsInstance(data["duration"], (int, float))
        self.assertIsInstance(data["cue_count"], int)
        self.assertIsInstance(data["confidence_threshold"], (int, float))
        self.assertIsInstance(data["low_confidence_words"], list)
        self.assertIsInstance(data["layout_warnings"], list)

        word_keys = {"start", "end", "text", "prob"}
        for word_dict in data["low_confidence_words"]:
            self.assertEqual(set(word_dict.keys()), word_keys)

        # Validate that the keys match what the CLI generates directly
        config = LayoutConfig(mode="words", upper=True, turkish_case=True)
        cues = layout(SAMPLE_WORDS, config, duration=7.20)
        cli_emitted_report = {
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
        self.assertEqual(set(data.keys()), set(cli_emitted_report.keys()))

    def test_demo_svg_structure_and_regeneration(self) -> None:
        import subprocess
        import sys

        demo_svg_path = ROOT / "docs/transcribe-demo.svg"
        self.assertTrue(demo_svg_path.is_file(), "docs/transcribe-demo.svg must exist.")
        content = demo_svg_path.read_text(encoding="utf-8")

        self.assertIn("<svg", content)
        self.assertIn("viewBox=", content)
        self.assertIn("subtool transcribe", content)
        self.assertIn(
            "subtool transcribe --words-json examples/transcribe/sample.words.json"
            " -o captions --format all --mode words --upper",
            content,
        )
        self.assertNotIn("--help", content)
        terminal_lines = [
            "".join(node.itertext())
            for node in ET.fromstring(content).findall(".//{http://www.w3.org/2000/svg}text")
        ]
        expected_srt = (EXAMPLES / "sample.srt").read_text(encoding="utf-8")
        for line in expected_srt.splitlines():
            if line:
                self.assertIn(line, terminal_lines)
        # Verify 3 window dots
        self.assertIn("#ff5f56", content)
        self.assertIn("#ffbd2e", content)
        self.assertIn("#27c93f", content)

        # Verify scripts/make-demo.py runs cleanly
        res = subprocess.run(
            [sys.executable, str(ROOT / "scripts/make-transcribe-demo.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(res.returncode, 0, f"make-demo.py failed: {res.stderr}")
        self.assertEqual(demo_svg_path.read_text(encoding="utf-8"), content)
