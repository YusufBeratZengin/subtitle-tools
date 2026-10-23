"""Additional unit tests targeting edge cases and branch coverage."""

from __future__ import annotations

import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from subtitle_tools.cli import main
from subtitle_tools.encoding import (
    check_mixed_newlines,
    detect_encoding,
    read_subtitle_file,
    write_subtitle_file,
)
from subtitle_tools.lint.fixer import auto_fix_tags, fix_document
from subtitle_tools.lint.rules import LintConfig
from subtitle_tools.operations.convert import convert
from subtitle_tools.operations.join import join
from subtitle_tools.operations.merge import merge
from subtitle_tools.operations.scale import parse_fps, scale
from subtitle_tools.operations.shift import shift
from subtitle_tools.operations.split import split
from subtitle_tools.parsers import (
    get_parser,
    get_writer,
    guess_format,
)
from subtitle_tools.types import AssStyle, Cue, SubtitleDocument


class TestCoverageEdges(unittest.TestCase):
    """Test suite covering operational edge cases and defensive checks."""

    def test_scale_parse_fps_and_errors(self) -> None:
        self.assertAlmostEqual(parse_fps(24), 24.0)
        self.assertAlmostEqual(parse_fps("24"), 24.0)
        self.assertAlmostEqual(parse_fps("25"), 25.0)
        self.assertAlmostEqual(parse_fps("30"), 30.0)
        self.assertAlmostEqual(parse_fps("50"), 50.0)
        self.assertAlmostEqual(parse_fps("60"), 60.0)
        self.assertAlmostEqual(parse_fps("120.0"), 120.0)

        with self.assertRaises(ValueError):
            parse_fps("invalid_fps")

        doc = SubtitleDocument(format="srt", cues=[Cue(start=1000, end=2000, text="Test")])
        with self.assertRaises(ValueError):
            scale(doc, from_fps=24, to_fps=0)

        with self.assertRaises(ValueError):
            scale(doc)

    def test_shift_edge_cases(self) -> None:
        empty_doc = SubtitleDocument(format="srt", cues=[])
        shifted_empty = shift(empty_doc, by_ms=1000)
        self.assertEqual(len(shifted_empty.cues), 0)

        doc = SubtitleDocument(format="srt", cues=[Cue(start=1000, end=2000, text="Test")])
        with self.assertRaises(ValueError):
            shift(doc)

        # drop_negative test
        doc_neg = SubtitleDocument(
            format="srt",
            cues=[Cue(start=500, end=1000, text="Dropped"), Cue(start=3000, end=5000, text="Kept")],
        )
        shifted = shift(doc_neg, by_ms=-1500, drop_negative=True)
        self.assertEqual(len(shifted.cues), 1)
        self.assertEqual(shifted.cues[0].text, "Kept")
        self.assertEqual(shifted.cues[0].start, 1500)
        self.assertEqual(shifted.cues[0].end, 3500)

    def test_split_edge_cases(self) -> None:
        doc = SubtitleDocument(format="srt", cues=[Cue(start=1000, end=2000, text="Test")])
        with self.assertRaises(ValueError):
            split(doc, duration_ms=0)

        empty_doc = SubtitleDocument(format="srt", cues=[])
        empty_split = split(empty_doc, duration_ms=1000)
        self.assertEqual(len(empty_split), 1)
        self.assertEqual(len(empty_split[0].cues), 0)

        # non-relative split
        doc_two = SubtitleDocument(
            format="srt",
            cues=[Cue(start=500, end=1500, text="C1"), Cue(start=3000, end=4000, text="C2")],
        )
        chunks = split(doc_two, duration_ms=2000, relative_times=False)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1].cues[0].start, 3000)
        self.assertEqual(chunks[1].cues[0].end, 4000)

    def test_join_edge_cases(self) -> None:
        with self.assertRaises(ValueError):
            join([])

        d1 = SubtitleDocument(format="srt", cues=[Cue(start=0, end=1000, text="Part 1")])
        d2 = SubtitleDocument(format="srt", cues=[Cue(start=0, end=1000, text="Part 2")])
        joined_no_seq = join([d1, d2], shift_sequential=False)
        self.assertEqual(len(joined_no_seq.cues), 2)
        self.assertEqual(joined_no_seq.cues[0].start, 0)
        self.assertEqual(joined_no_seq.cues[1].start, 0)

    def test_merge_edge_cases(self) -> None:
        d1 = SubtitleDocument(format="srt", cues=[Cue(start=1000, end=3000, text="Top")])
        d2 = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1500, end=3500, text="Bottom"),
                Cue(start=5000, end=6000, text="Unmatched D2"),
            ],
        )

        # Primary timing
        merged_prim = merge(d1, d2, timing="primary", keep_unmatched=False)
        self.assertEqual(len(merged_prim.cues), 1)
        self.assertEqual(merged_prim.cues[0].start, 1000)
        self.assertEqual(merged_prim.cues[0].end, 3000)
        self.assertIn("Top\nBottom", merged_prim.cues[0].text)

        # Secondary timing
        merged_sec = merge(d1, d2, timing="secondary", keep_unmatched=True)
        self.assertEqual(merged_sec.cues[0].start, 1500)
        self.assertEqual(merged_sec.cues[0].end, 3500)
        self.assertEqual(len(merged_sec.cues), 2)
        self.assertEqual(merged_sec.cues[1].text, "Unmatched D2")

    def test_convert_edge_cases(self) -> None:
        doc = SubtitleDocument(format="srt", cues=[Cue(start=1000, end=2000, text="Hello")])
        with self.assertRaises(ValueError):
            convert(doc, target_format="mp4")

        ass_doc = SubtitleDocument(
            format="ass",
            cues=[Cue(start=1000, end=2000, text="{\\b1}Bold{\\b0} text")],
        )
        vtt_doc = convert(ass_doc, target_format="vtt", strip_incompatible_tags=True)
        self.assertEqual(vtt_doc.format, "vtt")
        self.assertEqual(vtt_doc.cues[0].text, "Bold text")
        self.assertEqual(vtt_doc.vtt_header, "WEBVTT")

        # Convert to ASS initializes default sections
        srt_to_ass = convert(doc, target_format="ass")
        self.assertEqual(srt_to_ass.format, "ass")
        self.assertTrue(len(srt_to_ass.ass_script_info) > 0)
        self.assertTrue(len(srt_to_ass.ass_styles) > 0)
        self.assertTrue(len(srt_to_ass.ass_events_format) > 0)

    def test_fixer_edge_cases(self) -> None:
        self.assertEqual(auto_fix_tags(""), "")
        self.assertEqual(auto_fix_tags("test}"), "test")
        self.assertEqual(auto_fix_tags("Line with <br> break and <hr> line"), "Line with <br> break and <hr> line")
        self.assertEqual(auto_fix_tags("<i><b>Mixed</foo> tags</b>"), "<i><b>Mixed tags</b></i>")
        self.assertEqual(auto_fix_tags("Unclosed <b>bold and <i>italic"), "Unclosed <b>bold and <i>italic</i></b>")

        # Negative duration with small delta (< min_duration_ms)
        cfg = LintConfig(min_duration_ms=500)
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1200, end=1000, text="Short inverted cue")],
        )
        fixed_doc, count = fix_document(doc, config=cfg)
        self.assertEqual(count, 1)
        self.assertEqual(fixed_doc.cues[0].start, 1200)
        self.assertEqual(fixed_doc.cues[0].end, 1700)

    def test_parsers_registry_and_guess_format(self) -> None:
        self.assertEqual(guess_format("movie.ssa"), "ass")
        self.assertEqual(guess_format("movie.webvtt"), "vtt")
        self.assertEqual(guess_format("unknown.txt", content="WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi"), "vtt")
        self.assertEqual(guess_format("unknown.txt", content="[Script Info]\nTitle: Test"), "ass")
        self.assertEqual(guess_format("unknown.txt", content="1\n00:00:01,000 --> 00:00:02,000\nHi"), "srt")

        with self.assertRaises(ValueError):
            guess_format("unknown.bin", content="No subtitle keywords here")

        with self.assertRaises(ValueError):
            get_parser("unsupported_fmt")

        with self.assertRaises(ValueError):
            get_writer("unsupported_fmt")

    def test_encoding_utilities(self) -> None:
        self.assertFalse(check_mixed_newlines(b"hello\nworld\n"))
        self.assertFalse(check_mixed_newlines(b"hello\r\nworld\r\n"))
        self.assertTrue(check_mixed_newlines(b"hello\r\nworld\n"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_out.srt"
            write_subtitle_file(file_path, "1\n00:00:01,000 --> 00:00:02,000\nLine\n", newline="\r\n")
            text, enc, has_bom, _has_mixed = read_subtitle_file(file_path, encoding="utf-8")
            self.assertEqual(enc, "utf-8")
            self.assertFalse(has_bom)
            self.assertIn("Line", text)

        # Fallback to latin-1 when invalid sequence for cp1254/cp1252 occurs
        raw = b"\x81\x8d\x8f\x90"  # Undefined bytes in Windows-1252 / 1254
        detected = detect_encoding(raw)
        self.assertIn(detected, ("latin-1", "cp1254"))

    def test_types_properties(self) -> None:
        cue = Cue(start=1000, end=3500, text="  Hello world  ")
        self.assertEqual(cue.duration, 2500)
        self.assertFalse(cue.is_empty)

        empty_cue = Cue(start=0, end=1000, text="   \n\t  ")
        self.assertTrue(empty_cue.is_empty)

        style = AssStyle(name="Custom", fontsize=24.0)
        ass_line = style.to_ass_line()
        self.assertTrue(ass_line.startswith("Style: Custom,Arial,24.0,"))

        style_with_raw = AssStyle(raw_line="Style: Predefined,Arial,20")
        self.assertEqual(style_with_raw.to_ass_line(), "Style: Predefined,Arial,20")

        doc = SubtitleDocument(format="srt", cues=[cue, empty_cue])
        self.assertEqual(doc.cue_count, 2)
        self.assertEqual(doc.total_duration, 3500)

        empty_doc = SubtitleDocument(format="srt", cues=[])
        self.assertEqual(empty_doc.total_duration, 0)

    def test_cli_additional_branches(self) -> None:
        # CLI no args raises SystemExit(2)
        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit) as cm:
                main([])
            self.assertEqual(cm.exception.code, 2)

        # CLI lint no files matched
        with patch("sys.stderr.write"):
            code = main(["lint", "non_existent_pattern_*.srt"])
            self.assertEqual(code, 1)

        # CLI info no files found
        with patch("sys.stderr.write"):
            code = main(["info", "non_existent_pattern_*.srt"])
            self.assertEqual(code, 1)

        # CLI lint clean document (no issues)
        with tempfile.TemporaryDirectory() as tmp_dir:
            clean_file = Path(tmp_dir) / "clean.srt"
            clean_file.write_text(
                "1\n00:00:01,000 --> 00:00:03,000\nHello\n",
                encoding="utf-8",
            )
            with patch("sys.stdout.write") as mock_stdout:
                code = main(["lint", str(clean_file)])
                self.assertEqual(code, 0)
                out = "".join(call.args[0] for call in mock_stdout.call_args_list)
                self.assertIn("No issues found", out)

    def test_main_module_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample = Path(tmp_dir) / "info_sample.srt"
            sample.write_text("1\n00:00:01,000 --> 00:00:03,000\nHello\n", encoding="utf-8")
            with (
                patch.object(sys, "argv", ["subtool", "info", str(sample)]),
                patch("sys.exit") as mock_exit,
            ):
                runpy.run_module("subtitle_tools", run_name="__main__")
                mock_exit.assert_called_with(0)


if __name__ == "__main__":
    unittest.main()
