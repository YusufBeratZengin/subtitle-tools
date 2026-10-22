"""Unit tests for Advanced SubStation Alpha (.ass / .ssa) parser and writer."""

import unittest

from subtitle_tools.parsers.ass import AssParser, AssWriter


class TestAss(unittest.TestCase):
    """Test suite for ASS parsing, unknown section preservation, and styling."""

    def setUp(self) -> None:
        self.parser = AssParser()
        self.writer = AssWriter()

    def test_parse_and_preserve_unknown_sections(self) -> None:
        ass_content = (
            "[Script Info]\n"
            "Title: Custom Test Subtitle\n"
            "ScriptType: v4.00+\n\n"
            "[Custom Project Settings]\n"
            "ActiveProject: 1\n"
            "VideoPath: video.mp4\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:04.00,Default,Alice,10,10,10,,Hello world!\\NSecond line of dialogue.\n"
            "Comment: 0,0:00:00.00,0:00:01.00,Default,,,0,0,0,,A comment\n\n"
            "[Extra Section At End]\n"
            "Key: Val\n"
        )
        doc = self.parser.parse(ass_content)
        self.assertEqual(len(doc.cues), 1)
        cue = doc.cues[0]
        self.assertEqual(cue.start, 1000)
        self.assertEqual(cue.end, 4000)
        self.assertEqual(cue.actor, "Alice")
        self.assertEqual(cue.style, "Default")
        self.assertEqual(cue.text, "Hello world!\nSecond line of dialogue.")

        # Check unknown sections preserved verbatim
        self.assertEqual(len(doc.ass_unknown_sections), 2)
        sec1_name, sec1_lines = doc.ass_unknown_sections[0]
        self.assertEqual(sec1_name, "[Custom Project Settings]")
        self.assertIn("ActiveProject: 1", sec1_lines)

        sec2_name, sec2_lines = doc.ass_unknown_sections[1]
        self.assertEqual(sec2_name, "[Extra Section At End]")
        self.assertIn("Key: Val", sec2_lines)

        # Write output and verify unknown sections are retained
        written = self.writer.write(doc)
        self.assertIn("[Custom Project Settings]", written)
        self.assertIn("ActiveProject: 1", written)
        self.assertIn("[Extra Section At End]", written)
        self.assertIn("Key: Val", written)
        self.assertIn(r"Hello world!\NSecond line of dialogue.", written)


if __name__ == "__main__":
    unittest.main()
