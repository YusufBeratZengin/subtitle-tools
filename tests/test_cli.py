"""Unit tests for the CLI interface (subtool)."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from subtitle_tools.cli import main


class TestCliUsageErrors(unittest.TestCase):
    """Usage errors are checked in subprocesses against a read-only fixture."""

    srt_file = Path(__file__).resolve().parent / "fixtures" / "sample.srt"

    def _assert_usage_error(self, command: str, *options: str) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [sys.executable, "-m", "subtitle_tools", command, str(self.srt_file), *options],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(result.stderr.startswith(f"subtool {command}: error: "), result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertEqual(result.stdout, "")

    def test_cli_shift_requires_mode(self) -> None:
        self._assert_usage_error("shift")

    def test_cli_shift_bad_timestamp(self) -> None:
        self._assert_usage_error("shift", "--by", "abc")

    def test_cli_scale_requires_mode(self) -> None:
        self._assert_usage_error("scale")

    def test_cli_convert_unknown_extension(self) -> None:
        output = self.srt_file.with_suffix(".xyz")
        self._assert_usage_error("convert", str(output))
        self.assertFalse(output.exists())

    def test_cli_invalid_option_combinations_and_values(self) -> None:
        cases = [
            ("shift", ["--by", "1s", "--to", "2s"]),
            ("shift", ["--to", "abc"]),
            ("shift", ["--by", "inf"]),
            ("scale", ["--from-fps", "24"]),
            ("scale", ["--to-fps", "25"]),
            ("scale", ["--factor", "2", "--from-fps", "24"]),
            ("scale", ["--factor", "2", "--to-fps", "25"]),
            ("scale", ["--from-fps", "abc", "--to-fps", "25"]),
            ("scale", ["--from-fps", "24", "--to-fps", "0"]),
            ("scale", ["--from-fps", "nan", "--to-fps", "25"]),
            ("scale", ["--factor", "abc"]),
            ("scale", ["--factor", "0"]),
            ("scale", ["--factor", "inf"]),
        ]
        for command, options in cases:
            with self.subTest(command=command, options=options):
                with (
                    patch("sys.stderr", new_callable=io.StringIO) as stderr,
                    self.assertRaises(SystemExit) as raised,
                ):
                    main([command, str(self.srt_file), *options])
                self.assertEqual(raised.exception.code, 2)
                self.assertNotIn("Traceback", stderr.getvalue())
                self.assertTrue(stderr.getvalue().startswith(f"subtool {command}: error: "))


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

    def test_cli_scale_fps_pair(self) -> None:
        output = self.path / "scaled.srt"
        self.assertEqual(main([
            "scale", str(self.srt_file), "--from-fps", "24", "--to-fps", "25", "-o", str(output),
        ]), 0)
        self.assertIn("00:00:00,960 --> 00:00:03,840", output.read_text(encoding="utf-8"))

    def test_cli_shift_zero_alignment(self) -> None:
        output = self.path / "aligned.srt"
        self.assertEqual(main(["shift", str(self.srt_file), "--to", "0ms", "-o", str(output)]), 0)
        self.assertIn("00:00:00,000 --> 00:00:03,000", output.read_text(encoding="utf-8"))

    def test_cli_data_error(self) -> None:
        self.srt_file.write_bytes(b"\xff")
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            code = main(["convert", str(self.srt_file), str(self.path / "out.vtt"), "--encoding", "utf-8"])
        self.assertEqual(code, 1)
        self.assertTrue(stderr.getvalue().startswith("subtool convert: error: "))
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_file_error(self) -> None:
        with (
            patch("subtitle_tools.cli.write_subtitle_file", side_effect=OSError("Cannot write output")),
            patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            code = main(["convert", str(self.srt_file), str(self.path / "out.vtt")])
        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), "subtool convert: error: Cannot write output\n")

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
            _tmp_out_path = Path(tmp_out.name)

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
