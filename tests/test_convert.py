"""Unit tests for subtitle format conversion."""

import unittest

from subtitle_tools.operations.convert import convert
from subtitle_tools.parsers.ass import AssWriter
from subtitle_tools.parsers.srt import SrtWriter
from subtitle_tools.parsers.vtt import VttWriter
from subtitle_tools.types import Cue, SubtitleDocument


class TestConvert(unittest.TestCase):
    """Test suite for format conversions between SRT, VTT, and ASS."""

    def test_convert_srt_to_vtt(self) -> None:
        srt_doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=4000, text="Line 1\nLine 2", index=1)],
        )
        vtt_doc = convert(srt_doc, "vtt")
        self.assertEqual(vtt_doc.format, "vtt")
        self.assertEqual(vtt_doc.vtt_header, "WEBVTT")

        output = VttWriter().write(vtt_doc)
        self.assertIn("WEBVTT", output)
        self.assertIn("00:00:01.000 --> 00:00:04.000\nLine 1\nLine 2", output)

    def test_convert_vtt_to_srt(self) -> None:
        vtt_doc = SubtitleDocument(
            format="vtt",
            cues=[
                Cue(
                    start=1000,
                    end=4000,
                    text="Hello VTT",
                    identifier="intro",
                    settings="align:start",
                )
            ],
        )
        srt_doc = convert(vtt_doc, "srt")
        self.assertEqual(srt_doc.format, "srt")
        self.assertIsNone(srt_doc.cues[0].identifier)
        self.assertIsNone(srt_doc.cues[0].settings)

        output = SrtWriter().write(srt_doc)
        self.assertIn("00:00:01,000 --> 00:00:04,000\nHello VTT", output)

    def test_convert_ass_to_srt_stripping_tags(self) -> None:
        ass_doc = SubtitleDocument(
            format="ass",
            cues=[
                Cue(
                    start=1000,
                    end=4000,
                    text=r"{\pos(100,200)\b1}Styled Text{\b0}",
                    index=1,
                )
            ],
        )
        srt_doc = convert(ass_doc, "srt", strip_incompatible_tags=True)
        self.assertEqual(srt_doc.format, "srt")
        self.assertEqual(srt_doc.cues[0].text, "Styled Text")

    def test_convert_srt_to_ass(self) -> None:
        srt_doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=4000, text="Plain Subtitle", index=1)],
        )
        ass_doc = convert(srt_doc, "ass")
        self.assertEqual(ass_doc.format, "ass")
        self.assertTrue(len(ass_doc.ass_script_info) > 0)
        self.assertTrue(len(ass_doc.ass_styles) > 0)

        output = AssWriter().write(ass_doc)
        self.assertIn("[Script Info]", output)
        self.assertIn("[V4+ Styles]", output)
        self.assertIn("[Events]", output)
        self.assertIn("Plain Subtitle", output)


if __name__ == "__main__":
    unittest.main()
