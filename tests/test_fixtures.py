"""Fixtures and round-trip integration tests."""

import unittest
from pathlib import Path

from subtitle_tools.encoding import read_subtitle_file
from subtitle_tools.parsers import parse, write

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFixtures(unittest.TestCase):
    """Test suite running against all repository fixture files."""

    def test_sample_srt_roundtrip(self) -> None:
        path = FIXTURES_DIR / "sample.srt"
        text, _enc, _, _ = read_subtitle_file(path)
        doc1 = parse(text, "srt")
        self.assertEqual(len(doc1.cues), 3)

        serialized = write(doc1, "srt")
        doc2 = parse(serialized, "srt")
        self.assertEqual(len(doc2.cues), 3)
        for c1, c2 in zip(doc1.cues, doc2.cues):
            self.assertEqual(c1.start, c2.start)
            self.assertEqual(c1.end, c2.end)
            self.assertEqual(c1.text, c2.text)

    def test_sample_vtt_roundtrip(self) -> None:
        path = FIXTURES_DIR / "sample.vtt"
        text, _enc, _, _ = read_subtitle_file(path)
        doc1 = parse(text, "vtt")
        self.assertEqual(len(doc1.cues), 3)
        self.assertTrue(len(doc1.vtt_styles) > 0)
        self.assertTrue(len(doc1.vtt_notes) > 0)

        serialized = write(doc1, "vtt")
        doc2 = parse(serialized, "vtt")
        self.assertEqual(len(doc2.cues), 3)
        self.assertEqual(doc1.vtt_styles, doc2.vtt_styles)
        self.assertEqual(doc1.vtt_notes, doc2.vtt_notes)

    def test_sample_ass_roundtrip(self) -> None:
        path = FIXTURES_DIR / "sample.ass"
        text, _enc, _, _ = read_subtitle_file(path)
        doc1 = parse(text, "ass")
        self.assertEqual(len(doc1.cues), 3)
        self.assertTrue(len(doc1.ass_unknown_sections) > 0)

        serialized = write(doc1, "ass")
        doc2 = parse(serialized, "ass")
        self.assertEqual(len(doc2.cues), 3)
        # Verify unknown section Aegisub Project Garbage is preserved
        self.assertTrue(any("Aegisub" in s[0] for s in doc2.ass_unknown_sections))

    def test_malformed_srt_resilience(self) -> None:
        path = FIXTURES_DIR / "malformed.srt"
        text, _, _, _ = read_subtitle_file(path)
        doc = parse(text, "srt")
        # Should parse valid cues without throwing unhandled exceptions
        self.assertGreater(len(doc.cues), 0)

    def test_malformed_vtt_resilience(self) -> None:
        path = FIXTURES_DIR / "malformed.vtt"
        text, _, _, _ = read_subtitle_file(path)
        doc = parse(text, "vtt")
        self.assertGreater(len(doc.cues), 0)

    def test_malformed_ass_resilience(self) -> None:
        path = FIXTURES_DIR / "malformed.ass"
        text, _, _, _ = read_subtitle_file(path)
        doc = parse(text, "ass")
        self.assertGreater(len(doc.cues), 0)
        # Should preserve both Custom Header Section and Extra Footer Section
        names = [s[0] for s in doc.ass_unknown_sections]
        self.assertIn("[Custom Header Section]", names)
        self.assertIn("[Extra Footer Section]", names)

    def test_encoding_fixtures(self) -> None:
        # 1. UTF-8 BOM
        text, enc, has_bom, _ = read_subtitle_file(FIXTURES_DIR / "encoding_utf8_bom.srt")
        self.assertEqual(enc, "utf-8-sig")
        self.assertTrue(has_bom)
        self.assertIn("BOM encoded", text)

        # 2. CP1252
        text, enc, _, _ = read_subtitle_file(FIXTURES_DIR / "encoding_cp1252.srt")
        self.assertEqual(enc, "cp1252")
        self.assertIn("René", text)

        # 3. CP1254
        text, enc, _, _ = read_subtitle_file(FIXTURES_DIR / "encoding_cp1254.srt")
        self.assertEqual(enc, "cp1254")
        self.assertIn("şapka", text)
        self.assertIn("yağmur", text)
        self.assertIn("ışık", text)


if __name__ == "__main__":
    unittest.main()
