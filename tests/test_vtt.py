"""Unit tests for WebVTT (.vtt) parser and writer."""

import unittest

from subtitle_tools.parsers.vtt import VttParser, VttWriter
from subtitle_tools.types import Cue, SubtitleDocument


class TestVtt(unittest.TestCase):
    """Test suite for WebVTT parsing, serialization, and block preservation."""

    def setUp(self) -> None:
        self.parser = VttParser()
        self.writer = VttWriter()

    def test_parse_vtt_with_styles_and_notes(self) -> None:
        content = (
            "WEBVTT - Chapter 1\n\n"
            "STYLE\n"
            "::cue {\n"
            "  color: yellow;\n"
            "}\n\n"
            "NOTE This is a translator comment\n\n"
            "cue-1\n"
            "00:01.000 --> 00:04.000 line:0% position:50% align:left\n"
            "Welcome to WebVTT!\n\n"
            "cue-2\n"
            "00:05.500 --> 00:08.250\n"
            "Second cue line\n"
        )
        doc = self.parser.parse(content)
        self.assertEqual(doc.vtt_header, "WEBVTT - Chapter 1")
        self.assertEqual(len(doc.vtt_styles), 1)
        self.assertIn("color: yellow;", doc.vtt_styles[0])
        self.assertEqual(len(doc.vtt_notes), 1)
        self.assertIn("translator comment", doc.vtt_notes[0])
        self.assertEqual(len(doc.cues), 2)

        cue1 = doc.cues[0]
        self.assertEqual(cue1.identifier, "cue-1")
        self.assertEqual(cue1.start, 1000)
        self.assertEqual(cue1.end, 4000)
        self.assertEqual(cue1.settings, "line:0% position:50% align:left")
        self.assertEqual(cue1.text, "Welcome to WebVTT!")

    def test_write_vtt(self) -> None:
        doc = SubtitleDocument(
            format="vtt",
            vtt_header="WEBVTT",
            vtt_styles=["STYLE\n::cue { color: red; }"],
            cues=[
                Cue(
                    start=1000,
                    end=4000,
                    text="Hello VTT",
                    identifier="intro",
                    settings="align:center",
                )
            ],
        )
        output = self.writer.write(doc)
        self.assertIn("WEBVTT", output)
        self.assertIn("STYLE\n::cue { color: red; }", output)
        self.assertIn("intro\n00:00:01.000 --> 00:00:04.000 align:center\nHello VTT", output)

    def test_roundtrip_vtt(self) -> None:
        content = (
            "WEBVTT\n\n"
            "STYLE\n"
            "::cue { color: cyan; }\n\n"
            "NOTE Introductory note\n\n"
            "cue-1\n"
            "00:00:01.000 --> 00:00:04.000 align:start\n"
            "Hello world\n"
        )
        doc = self.parser.parse(content)
        serialized = self.writer.write(doc)
        self.assertEqual(serialized, content)


if __name__ == "__main__":
    unittest.main()
