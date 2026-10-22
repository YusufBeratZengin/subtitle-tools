"""Unit tests for subtitle linting rules."""

import unittest

from subtitle_tools.lint.linter import check_unbalanced_tags, lint_document
from subtitle_tools.lint.rules import LintConfig
from subtitle_tools.types import Cue, SubtitleDocument


class TestLint(unittest.TestCase):
    """Test suite for lint rules and issue detection."""

    def test_overlap_rule(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=4000, text="First", index=1),
                Cue(start=3500, end=6000, text="Overlap", index=2),
            ],
        )
        issues = lint_document(doc)
        rule_ids = [i.rule_id for i in issues]
        self.assertIn("overlap", rule_ids)
        overlap_issue = next(i for i in issues if i.rule_id == "overlap")
        self.assertEqual(overlap_issue.cue_index, 2)
        self.assertTrue(overlap_issue.fixable)

    def test_negative_and_zero_duration_rules(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=4000, end=3000, text="Negative duration", index=1),
                Cue(start=5000, end=5000, text="Zero duration", index=2),
            ],
        )
        issues = lint_document(doc)
        rule_ids = [i.rule_id for i in issues]
        self.assertIn("negative-duration", rule_ids)
        self.assertIn("zero-duration", rule_ids)

    def test_duration_limits(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=1200, text="Too short (200ms)", index=1),
                Cue(start=2000, end=11000, text="Too long (9000ms)", index=2),
            ],
        )
        config = LintConfig(min_duration_ms=500, max_duration_ms=7000)
        issues = lint_document(doc, config=config)
        rule_ids = [i.rule_id for i in issues]
        self.assertIn("too-short-duration", rule_ids)
        self.assertIn("too-long-duration", rule_ids)

    def test_cps_limit_rule(self) -> None:
        # 1000ms duration, 30 visible characters -> 30 CPS (over default 17 CPS)
        text = "This is a very fast reading line of text!"
        doc = SubtitleDocument(
            format="srt",
            cues=[Cue(start=1000, end=2000, text=text, index=1)],
        )
        issues = lint_document(doc, config=LintConfig(max_cps=17.0))
        rule_ids = [i.rule_id for i in issues]
        self.assertIn("cps-limit", rule_ids)

    def test_line_length_and_count_rules(self) -> None:
        long_line = "A" * 50  # Over default 42 chars
        three_lines = "Line 1\nLine 2\nLine 3"
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=5000, text=long_line, index=1),
                Cue(start=6000, end=9000, text=three_lines, index=2),
            ],
        )
        issues = lint_document(doc, config=LintConfig(max_line_length=42, max_lines=2))
        rule_ids = [i.rule_id for i in issues]
        self.assertIn("line-length", rule_ids)
        self.assertIn("line-count", rule_ids)

    def test_empty_cue_rule(self) -> None:
        doc = SubtitleDocument(
            format="srt",
            cues=[
                Cue(start=1000, end=4000, text="   ", index=1),
                Cue(start=5000, end=8000, text="<i></i>", index=2),
            ],
        )
        issues = lint_document(doc)
        empty_issues = [i for i in issues if i.rule_id == "empty-cue"]
        self.assertEqual(len(empty_issues), 2)

    def test_unbalanced_tags_checker(self) -> None:
        self.assertFalse(check_unbalanced_tags("<i>Italic text</i>")[0])
        self.assertFalse(check_unbalanced_tags("<b><i>Nested text</i></b>")[0])
        self.assertFalse(check_unbalanced_tags(r"{\pos(100,200)}Ass text")[0])

        is_unb, desc = check_unbalanced_tags("<i>Unclosed tag")
        self.assertTrue(is_unb)
        self.assertIn("<i>", desc)

        is_unb, desc = check_unbalanced_tags(r"{\pos(100,200)Missing closing bracket")
        self.assertTrue(is_unb)

    def test_encoding_issues_flagged(self) -> None:
        doc = SubtitleDocument(format="srt", cues=[])
        issues = lint_document(doc, has_bom=True, has_mixed_newlines=True)
        rule_ids = [i.rule_id for i in issues]
        self.assertEqual(rule_ids.count("encoding-issue"), 2)


if __name__ == "__main__":
    unittest.main()
