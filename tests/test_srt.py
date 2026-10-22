"""Unit tests for SubRip (.srt) parser and writer."""

import unittest

from subtitle_tools.parsers.srt import SrtParser, SrtWriter
from subtitle_tools.types import Cue, SubtitleDocument


class TestSrt(unittest.TestCase):
    """Test suite for SRT parsing, serialization, and edge cases."""

    def setUp(self) -> None:
        self.parser = SrtParser()
        self.writer = SrtWriter()

    def test_parse_standard_srt(self) -> None:
        sample = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "First subtitle line\n"
            "Second subtitle line\n\n"
            "2\n"
            "00:00:05,500 --> 00:00:08,250\n"
            "Next subtitle\n"
        )
        doc = self.parser.parse(sample)
        self.assertEqual(len(doc.cues), 2)
        self.assertEqual(doc.cues[0].start, 1000)
        self.assertEqual(doc.cues[0].end, 4000)
        self.assertEqual(doc.cues[0].text, "First subtitle line\nSecond subtitle line")
        self.assertEqual(doc.cues[1].start, 5500)
        self.assertEqual(doc.cues[1].end, 8250)
        self.assertEqual(doc.cues[1].text, "Next subtitle")

    def test_parse_malformed_srt(self) -> None:
        # Missing index numbers, dot instead of comma, redundant whitespace
        sample = (
            "\n\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "Line without index number\n\n\n"
            "2\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "Second line\n"
        )
        doc = self.parser.parse(sample)
        self.assertEqual(len(doc.cues), 2)
        self.assertEqual(doc.cues[0].start, 1000)
        self.assertEqual(doc.cues[0].text, "Line without index number")

    def test_write_standard_srt(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=4000, text="Hello", index=1),
                Cue(start=5000, end=8000, text="World", index=2),
            ],
        )
        output = self.writer.write(doc)
        expected = "1\n00:00:01,000 --> 00:00:04,000\nHello\n\n2\n00:00:05,000 --> 00:00:08,000\nWorld\n"
        self.assertEqual(output, expected)

    def test_roundtrip_srt(self) -> None:
        original = (
            "1\n"
            "00:01:00,000 --> 00:01:05,000\n"
            "Roundtrip test line\n\n"
            "2\n"
            "00:01:10,000 --> 00:01:15,000\n"
            "Another line\n"
        )
        doc = self.parser.parse(original)
        written = self.writer.write(doc)
        self.assertEqual(written, original)


if __name__ == "__main__":
    unittest.main()
