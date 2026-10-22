"""Unit tests for the CLI interface (subtool)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from subtitle_tools.cli import main


class TestCli(unittest.TestCase):
    """Test suite for subtool CLI commands."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp_dir.name)

        # Create basic sample files
        self.srt_file = self.path / "sample.srt"
        self.srt_file.write_text(
            "1\n00:00:01,000 --> 00:00:04,000\nHello <i>World</i>\n\n"
            "2\n00:00:05,000 --> 00:00:08,000\nSecond cue\n",
            encoding="utf-8",
        )

        self.srt_file2 = self.path / "sample2.srt"
        self.srt_file2.write_text(
            "1\n00:00:01,200 --> 00:00:04,100\nMerhaba Dunya\n\n"
            "2\n00:00:05,100 --> 00:00:08,200\nIkinci satir\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_cli_convert(self) -> None:
        out_vtt = self.path / "out.vtt"
        code = main(["convert", str(self.srt_file), str(out_vtt)])
        self.assertEqual(code, 0)
        self.assertTrue(out_vtt.is_file())
        content = out_vtt.read_text(encoding="utf-8")
        self.assertIn("WEBVTT", content)
        self.assertIn("00:00:01.000 --> 00:00:04.000", content)

    def test_cli_shift(self) -> None:
        out_srt = self.path / "shifted.srt"
        code = main(["shift", str(self.srt_file), "-o", str(out_srt), "--by", "1500ms"])
        self.assertEqual(code, 0)
        content = out_srt.read_text(encoding="utf-8")
        self.assertIn("00:00:02,500 --> 00:00:05,500", content)

    def test_cli_scale(self) -> None:
        out_srt = self.path / "scaled.srt"
        code = main(["scale", str(self.srt_file), "-o", str(out_srt), "--factor", "2.0"])
        self.assertEqual(code, 0)
        content = out_srt.read_text(encoding="utf-8")
        self.assertIn("00:00:02,000 --> 00:00:08,000", content)

    def test_cli_merge(self) -> None:
        out_merged = self.path / "merged.srt"
        code = main(["merge", str(self.srt_file), str(self.srt_file2), "-o", str(out_merged)])
        self.assertEqual(code, 0)
        content = out_merged.read_text(encoding="utf-8")
        self.assertIn("Hello <i>World</i>\nMerhaba Dunya", content)

    def test_cli_split(self) -> None:
        code = main(["split", str(self.srt_file), "--duration", "5s", "-o", "part"])
        self.assertEqual(code, 0)
        part1 = self.path / "part_part01.srt"
        self.assertTrue(part1.is_file())

    def test_cli_join(self) -> None:
        out_joined = self.path / "joined.srt"
        code = main(["join", str(self.srt_file), str(self.srt_file2), "-o", str(out_joined), "--gap", "500ms"])
        self.assertEqual(code, 0)
        content = out_joined.read_text(encoding="utf-8")
        self.assertIn("Second cue", content)
        self.assertIn("Ikinci satir", content)

    def test_cli_renumber(self) -> None:
        out_renum = self.path / "renum.srt"
        code = main(["renumber", str(self.srt_file), "-o", str(out_renum), "--start", "10"])
        self.assertEqual(code, 0)
        content = out_renum.read_text(encoding="utf-8")
        self.assertIn("10\n00:00:01,000", content)

    def test_cli_strip_tags(self) -> None:
        out_clean = self.path / "clean.srt"
        code = main(["strip-tags", str(self.srt_file), "-o", str(out_clean)])
        self.assertEqual(code, 0)
        content = out_clean.read_text(encoding="utf-8")
        self.assertIn("Hello World", content)
        self.assertNotIn("<i>", content)

    def test_cli_lint_json(self) -> None:
        # Create a malformed file
        bad_file = self.path / "bad.srt"
        bad_file.write_text("1\n00:00:04,000 --> 00:00:02,000\nNegative duration\n", encoding="utf-8")

        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_out:
            tmp_out_path = Path(tmp_out.name)

        with patch("sys.stdout.write") as mock_stdout:
            code = main(["lint", str(bad_file), "--format", "json"])
            self.assertEqual(code, 1)  # Has error
            # Combine calls
            all_output = "".join(call.args[0] for call in mock_stdout.call_args_list)
            data = json.loads(all_output)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["issues"][0]["rule_id"], "negative-duration")

    def test_cli_lint_fix(self) -> None:
        bad_file = self.path / "to_fix.srt"
        bad_file.write_text(
            "1\n00:00:01,000 --> 00:00:04,000\n<i>Unclosed italic\n\n"
            "2\n00:00:05,000 --> 00:00:05,000\nZero duration\n",
            encoding="utf-8",
        )
        code = main(["lint", str(bad_file), "--fix"])
        self.assertEqual(code, 0)
        fixed_text = bad_file.read_text(encoding="utf-8")
        self.assertIn("<i>Unclosed italic</i>", fixed_text)

    def test_cli_info(self) -> None:
        code = main(["info", str(self.srt_file)])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
