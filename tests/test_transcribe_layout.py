"""Entirely invented Turkish phrases; no model or personal data is used."""

import math
import unittest
from dataclasses import replace
from itertools import pairwise

from subtitle_tools.transcribe import LayoutConfig, Word, WordCue, layout, turkish_upper
from subtitle_tools.transcribe.layout import layout_warnings


def phrase(text: str, *, step: float = 0.5, start: float = 0) -> tuple[Word, ...]:
    return tuple(
        Word(start + i * step, start + i * step + step * 0.8, token, 0.9)
        for i, token in enumerate(text.split())
    )


class ModelTests(unittest.TestCase):
    def test_word_valid_boundaries(self) -> None:
        self.assertEqual(Word(0, 1, "ışık", 0).prob, 0)
        self.assertEqual(Word(0, 1, "için", 1).prob, 1)

    def test_word_invalid(self) -> None:
        for args in [
            (-1, 1, "bir", 1),
            (1, 1, "bir", 1),
            (2, 1, "bir", 1),
            (0, math.inf, "bir", 1),
            (math.nan, 1, "bir", 1),
            (0, 1, "", 1),
            (0, 1, "iki kelime", 1),
            (0, 1, "satır\n", 1),
            (0, 1, "bir", -0.1),
            (0, 1, "bir", 1.1),
            (0, 1, "bir", math.nan),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Word(*args)

    def test_cue_valid(self) -> None:
        words = phrase("bir gün")
        cue = WordCue(0, 2, (words[:1], words[1:]))
        self.assertEqual(cue.text, "bir\ngün")
        self.assertEqual(cue.words, words)

    def test_cue_invalid(self) -> None:
        word = Word(1, 2, "ışık")
        for args in [
            (0, 2, ()),
            (0, 2, ((),)),
            (1.5, 2, ((word,),)),
            (0, 1.5, ((word,),)),
            (-1, 2, ((word,),)),
            (0, math.inf, ((word,),)),
            (0, 2, ((word, word),)),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                WordCue(*args)


class LayoutTests(unittest.TestCase):
    def test_config_valid(self) -> None:
        self.assertEqual(LayoutConfig(max_chars=1, max_lines=4, mode="words").max_chars, 1)

    def test_config_invalid(self) -> None:
        for kwargs in [
            {"max_chars": 0},
            {"max_chars": True},
            {"max_chars": 1.5},
            {"max_lines": 0},
            {"max_lines": 5},
            {"max_lines": True},
            {"pause_threshold": 0},
            {"pause_threshold": math.inf},
            {"min_duration": -1},
            {"min_duration": math.nan},
            {"max_cps": 0},
            {"max_cps": math.inf},
            {"mode": "invalid"},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                LayoutConfig(**kwargs)

    def test_empty(self) -> None:
        self.assertEqual(layout([]), ())
        self.assertEqual(layout([], duration=0), ())

    def test_order_duration_validation(self) -> None:
        words = phrase("bir gün")
        for items, duration in [(words[::-1], None), (words, 0), (words, math.nan), ((), -1)]:
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                layout(items, duration=duration)

    def test_turkish_upper(self) -> None:
        self.assertEqual(
            turkish_upper("iyi ışık için, küçük bir öykü."), "İYİ IŞIK İÇİN, KÜÇÜK BİR ÖYKÜ."
        )
        original = phrase("iyi ışık")
        cues = layout(original, LayoutConfig(upper=True))
        self.assertEqual([w.text for c in cues for w in c.words], ["İYİ", "IŞIK"])
        self.assertEqual(original[0].text, "iyi")

    def test_spatial_limits_and_preservation(self) -> None:
        words = phrase("Bugün küçük bir öykü var ve ışık yavaş yavaş değişiyor.")
        cues = layout(words, duration=10)
        self.assertEqual(tuple(w for c in cues for w in c.words), words)
        for cue in cues:
            self.assertLessEqual(len(cue.lines), 2)
            self.assertTrue(all(len(line) <= 18 for line in cue.text.splitlines()))
        self.assertTrue(all(a.end <= b.start for a, b in pairwise(cues)))

    def test_conjunction_not_stranded(self) -> None:
        for joiner in ("ve", "ama", "ki", "de", "da", "VE", "Kİ"):
            with self.subTest(joiner=joiner):
                cues = layout(phrase(f"ışık {joiner} renk"), LayoutConfig(max_chars=9))
                self.assertTrue(all(line[-1].text != joiner for c in cues for line in c.lines))

    def test_conjunction_moved_to_next_cue(self) -> None:
        config = LayoutConfig(max_chars=9, max_lines=1, min_duration=0.1, max_cps=100)
        cues = layout(phrase("ışık ve renk"), config)
        self.assertEqual([c.text for c in cues], ["ışık", "ve renk"])

    def test_pause_boundary_and_no_merge_across_pause(self) -> None:
        words = (Word(0, 0.2, "bir"), Word(2, 2.2, "gün"))
        cues = layout(words, duration=3)
        self.assertEqual(len(cues), 2)
        self.assertLessEqual(cues[0].end, cues[1].start)

    def test_conjunction_does_not_move_across_long_pause(self) -> None:
        words = (*phrase("ışık ve"), Word(4, 5, "renk"))
        cues = layout(words, duration=6)
        self.assertEqual(cues[0].words, words[:2])
        self.assertEqual(cues[1].words, words[2:])

    def test_punctuation_boundary(self) -> None:
        cues = layout(
            phrase("Işık değişti. Renk kaldı.", step=1), LayoutConfig(min_duration=0.1, max_cps=100)
        )
        self.assertEqual(len(cues), 2)
        self.assertTrue(cues[0].text.endswith("değişti."))

    def test_words_mode_and_short_cue_merge(self) -> None:
        words = phrase("bir gün", step=1)
        separate = layout(words, LayoutConfig(mode="words", min_duration=0.1, max_cps=100))
        self.assertEqual(len(separate), 2)
        merged = layout(phrase("bir gün", step=0.1), LayoutConfig(mode="words"), duration=1)
        self.assertEqual(len(merged), 1)
        self.assertGreaterEqual(merged[0].end - merged[0].start, 0.8)

    def test_extend_into_silence_capped_at_duration(self) -> None:
        words = (Word(0, 0.2, "ışık"),)
        self.assertEqual(layout(words, duration=2)[0].end, 0.8)
        self.assertEqual(layout(words, duration=0.4)[0].end, 0.4)
        self.assertEqual(layout(words)[0].end, 0.2)

    def test_reading_speed_drives_duration(self) -> None:
        cue = layout(
            (Word(0, 0.1, "değişiyor"),), LayoutConfig(min_duration=0.1, max_cps=3), duration=5
        )[0]
        self.assertEqual(cue.end, 3)

    def test_impossible_constraints_reported(self) -> None:
        config = LayoutConfig(max_chars=3)
        cues = layout((Word(0, 0.1, "değişiyor"),), config)
        codes = layout_warnings(cues, config)[0]["codes"]
        self.assertIn("long_word", codes)
        self.assertIn("short_duration", codes)
        self.assertIn("reading_speed", codes)
        self.assertEqual(cues[0].text, "değişiyor")

    def test_no_warnings_for_feasible_case(self) -> None:
        config = LayoutConfig()
        self.assertEqual(layout_warnings(layout(phrase("bir gün"), duration=3), config), [])

    def test_many_generated_phrases_preserve_words_and_limits(self) -> None:
        for width in (8, 12, 18, 30):
            for count in range(1, 40):
                words = tuple(
                    replace(Word(i * 0.4, i * 0.4 + 0.3, "ışık"), prob=0.7) for i in range(count)
                )
                cues = layout(words, LayoutConfig(max_chars=width), duration=count * 0.4)
                self.assertEqual(tuple(w for c in cues for w in c.words), words)
                self.assertTrue(all(len(c.lines) <= 2 for c in cues))
                self.assertTrue(
                    all(len(line) <= width for c in cues for line in c.text.splitlines())
                )


class RegressionTests(unittest.TestCase):
    def test_sentence_final_joiner_is_not_carried_into_next_cue(self) -> None:
        # "de." closes a sentence; it must stay with its own sentence.
        words = phrase("Dün akşam eve geldik. Sen de. Sonra çok güzel bir film izledik", step=1.0)
        cues = layout(words, LayoutConfig())
        texts = [c.text.replace("\n", " ") for c in cues]
        self.assertTrue(any(t.endswith("Sen de.") for t in texts), texts)
        self.assertFalse(any(t.startswith("de.") for t in texts), texts)

    def test_sentence_final_joiner_has_no_trailing_conjunction_warning(self) -> None:
        config = LayoutConfig()
        words = phrase("Sen de. Sonra gittik", step=1.0)
        cues = layout(words, config)
        self.assertEqual(layout_warnings(cues, config), [])

    def test_non_turkish_uppercase_keeps_plain_i(self) -> None:
        words = phrase("it is fine")
        cues = layout(words, LayoutConfig(upper=True, turkish_case=False))
        self.assertEqual([w.text for c in cues for w in c.words], ["IT", "IS", "FINE"])
        cues = layout(words, LayoutConfig(upper=True))
        self.assertEqual([w.text for c in cues for w in c.words], ["İT", "İS", "FİNE"])
