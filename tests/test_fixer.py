"""Unit tests for safe auto-fixing functionality."""

import unittest

from subtitle_tools.lint.fixer import auto_fix_tags, fix_document
from subtitle_tools.types import Cue, SubtitleDocument


class TestFixer(unittest.TestCase):
    """Test suite for auto-fix rules."""

    def test_auto_fix_tags(self) -> None:
        self.assertEqual(auto_fix_tags("<i>Hello"), "<i>Hello</i>")
        self.assertEqual(auto_fix_tags("<b><i>Nested"), "<b><i>Nested</i></b>")
        self.assertEqual(auto_fix_tags("Orphan</i>"), "Orphan")
        self.assertEqual(auto_fix_tags(r"{\pos(100,200)Text"), r"{\pos(100,200)Text}")

    def test_fix_document_drops_empty_cues(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=4000, text="Keep me", index=1),
                Cue(start=5000, end=8000, text="   ", index=2),
                Cue(start=9000, end=12000, text="Also keep me", index=3),
            ],
        )
        fixed_doc, count = fix_document(doc)
        self.assertEqual(len(fixed_doc.cues), 2)
        self.assertEqual(fixed_doc.cues[0].text, "Keep me")
        self.assertEqual(fixed_doc.cues[0].index, 1)
        self.assertEqual(fixed_doc.cues[1].text, "Also keep me")
        self.assertEqual(fixed_doc.cues[1].index, 2)
        self.assertGreater(count, 0)

    def test_fix_document_resolves_small_overlap(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=4000, text="First", index=1),
                Cue(start=3800, end=6000, text="Second (overlaps by 200ms)", index=2),
            ],
        )
        fixed_doc, count = fix_document(doc)
        self.assertEqual(fixed_doc.cues[0].end, 3800)
        self.assertEqual(fixed_doc.cues[1].start, 3800)
        self.assertGreater(count, 0)

    def test_fix_document_resolves_zero_duration(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=1000, text="Zero duration", index=1)],
        )
        fixed_doc, count = fix_document(doc)
        self.assertEqual(fixed_doc.cues[0].start, 1000)
        self.assertEqual(fixed_doc.cues[0].end, 1500)
        self.assertGreater(count, 0)

    def test_fix_document_repairs_unbalanced_tags(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=4000, text="<i>Unclosed italic", index=1)],
        )
        fixed_doc, count = fix_document(doc)
        self.assertEqual(fixed_doc.cues[0].text, "<i>Unclosed italic</i>")
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
