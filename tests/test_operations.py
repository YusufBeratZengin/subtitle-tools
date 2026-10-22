"""Unit tests for subtitle operations (shift, scale, merge, split, join, renumber, strip_tags)."""

import unittest

from subtitle_tools.operations.join import join
from subtitle_tools.operations.merge import merge
from subtitle_tools.operations.renumber import renumber
from subtitle_tools.operations.scale import scale
from subtitle_tools.operations.shift import shift
from subtitle_tools.operations.split import split
from subtitle_tools.operations.tags import strip_formatting_tags, strip_tags
from subtitle_tools.types import Cue, SubtitleDocument


class TestOperations(unittest.TestCase):
    """Test suite for subtitle transformation operations."""

    def test_shift_by_offset(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=4000, text="A"), Cue(start=5000, end=8000, text="B")],
        )
        shifted = shift(doc, by_ms="1500ms")
        self.assertEqual(shifted.cues[0].start, 2500)
        self.assertEqual(shifted.cues[0].end, 5500)
        self.assertEqual(shifted.cues[1].start, 6500)
        self.assertEqual(shifted.cues[1].end, 9500)

    def test_shift_negative_and_clamp(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=3000, text="A"), Cue(start=5000, end=7000, text="B")],
        )
        shifted = shift(doc, by_ms="-2000ms")
        self.assertEqual(shifted.cues[0].start, 0)
        self.assertEqual(shifted.cues[0].end, 1000)
        self.assertEqual(shifted.cues[1].start, 3000)
        self.assertEqual(shifted.cues[1].end, 5000)

    def test_shift_align_first(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=3000, end=6000, text="A"), Cue(start=8000, end=11000, text="B")],
        )
        # Shift so first cue starts at 1000ms
        shifted = shift(doc, to_ms="00:00:01,000")
        self.assertEqual(shifted.cues[0].start, 1000)
        self.assertEqual(shifted.cues[0].end, 4000)
        self.assertEqual(shifted.cues[1].start, 6000)
        self.assertEqual(shifted.cues[1].end, 9000)

    def test_scale_framerate(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=25000, end=50000, text="A")],
        )
        # 25 fps to 23.976 fps: timestamps scale by 25 / (24000/1001) ~ 1.0427
        scaled = scale(doc, from_fps=25, to_fps=23.976)
        self.assertEqual(scaled.cues[0].start, 26068)
        self.assertEqual(scaled.cues[0].end, 52135)

    def test_scale_direct_factor(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=2000, text="A")],
        )
        scaled = scale(doc, factor=1.5)
        self.assertEqual(scaled.cues[0].start, 1500)
        self.assertEqual(scaled.cues[0].end, 3000)

    def test_merge_stacked_cues(self) -> None:
        doc_en = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=4000, text="Hello"),
                Cue(start=5000, end=8000, text="Goodbye"),
            ],
        )
        doc_tr = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1200, end=3800, text="Merhaba"),
                Cue(start=5100, end=7900, text="Hoscakal"),
            ],
        )
        merged = merge(doc_en, doc_tr, separator="\n")
        self.assertEqual(len(merged.cues), 2)
        self.assertEqual(merged.cues[0].text, "Hello\nMerhaba")
        self.assertEqual(merged.cues[1].text, "Goodbye\nHoscakal")
        self.assertEqual(merged.cues[0].start, 1000)
        self.assertEqual(merged.cues[0].end, 4000)

    def test_split_by_duration(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=5000, end=8000, text="Part 1 Cue"),
                Cue(start=65000, end=68000, text="Part 2 Cue"),
            ],
        )
        # Split every 60 seconds (60000ms)
        parts = split(doc, duration_ms="60s", relative_times=True)
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0].cues), 1)
        self.assertEqual(parts[0].cues[0].text, "Part 1 Cue")
        self.assertEqual(parts[0].cues[0].start, 5000)

        self.assertEqual(len(parts[1].cues), 1)
        self.assertEqual(parts[1].cues[0].text, "Part 2 Cue")
        # Relative time: 65000 - 60000 = 5000ms
        self.assertEqual(parts[1].cues[0].start, 5000)
        self.assertEqual(parts[1].cues[0].end, 8000)

    def test_join_documents(self) -> None:
        doc1 = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=4000, text="Doc 1")],
        )
        doc2 = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=3000, text="Doc 2")],
        )
        joined = join([doc1, doc2], gap_ms="1000ms", shift_sequential=True)
        self.assertEqual(len(joined.cues), 2)
        self.assertEqual(joined.cues[0].start, 1000)
        self.assertEqual(joined.cues[0].end, 4000)
        # Shifted: doc1 ended at 4000 + 1000 gap = 5000 base offset
        self.assertEqual(joined.cues[1].start, 6000)
        self.assertEqual(joined.cues[1].end, 8000)
        self.assertEqual(joined.cues[1].index, 2)

    def test_renumber(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=5000, end=8000, text="B", index=99),
                Cue(start=1000, end=3000, text="A", index=42),
            ],
        )
        renumbered = renumber(doc, start_index=1, sort_first=True)
        self.assertEqual(renumbered.cues[0].text, "A")
        self.assertEqual(renumbered.cues[0].index, 1)
        self.assertEqual(renumbered.cues[1].text, "B")
        self.assertEqual(renumbered.cues[1].index, 2)

    def test_strip_formatting_tags(self) -> None:
        raw = "<i>Hello</i> <b>world</b>! <v Speaker 1>Welcome</v> &amp; enjoy. {\\pos(100,200)\\b1}Styled{\\b0}"
        stripped = strip_formatting_tags(raw)
        self.assertEqual(stripped, "Hello world! Welcome & enjoy. Styled")

    def test_strip_tags_operation(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=2000, text="<b>Bold</b> text")],
        )
        cleaned = strip_tags(doc)
        self.assertEqual(cleaned.cues[0].text, "Bold text")


if __name__ == "__main__":
    unittest.main()
