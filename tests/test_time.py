"""Unit tests for time parsing and formatting."""

import unittest

from subtitle_tools.time import (
    format_ass_time,
    format_srt_time,
    format_vtt_time,
    parse_offset,
    parse_time,
    split_ms,
)


class TestTime(unittest.TestCase):
    """Test suite for timestamp parsing and formatting."""

    def test_parse_srt_timestamp(self) -> None:
        self.assertEqual(parse_time("00:01:23,456"), 83456)
        self.assertEqual(parse_time("01:00:00,000"), 3600000)
        self.assertEqual(parse_time("00:00:00,500"), 500)

    def test_parse_vtt_timestamp(self) -> None:
        self.assertEqual(parse_time("00:01:23.456"), 83456)
        self.assertEqual(parse_time("01:23.456"), 83456)
        self.assertEqual(parse_time("00:05.100"), 5100)

    def test_parse_ass_timestamp(self) -> None:
        # Centiseconds
        self.assertEqual(parse_time("0:01:23.45"), 83450)
        self.assertEqual(parse_time("1:00:00.00"), 3600000)
        self.assertEqual(parse_time("0:00:00.05"), 50)

    def test_parse_offset_units(self) -> None:
        self.assertEqual(parse_offset("1500ms"), 1500)
        self.assertEqual(parse_offset("+1500ms"), 1500)
        self.assertEqual(parse_offset("-200ms"), -200)
        self.assertEqual(parse_offset("1.5s"), 1500)
        self.assertEqual(parse_offset("-2.5s"), -2500)
        self.assertEqual(parse_offset("1m"), 60000)
        self.assertEqual(parse_offset("2h"), 7200000)

    def test_parse_raw_numbers(self) -> None:
        self.assertEqual(parse_time("1500"), 1500)
        self.assertEqual(parse_time("-500"), -500)

    def test_parse_invalid(self) -> None:
        with self.assertRaises(ValueError):
            parse_time("")
        with self.assertRaises(ValueError):
            parse_time("not-a-time")
        with self.assertRaises(ValueError):
            parse_time("100xyz")

    def test_format_srt_time(self) -> None:
        self.assertEqual(format_srt_time(0), "00:00:00,000")
        self.assertEqual(format_srt_time(83456), "00:01:23,456")
        self.assertEqual(format_srt_time(3661005), "01:01:01,005")
        self.assertEqual(format_srt_time(-100), "00:00:00,000")

    def test_format_vtt_time(self) -> None:
        self.assertEqual(format_vtt_time(0), "00:00:00.000")
        self.assertEqual(format_vtt_time(83456), "00:01:23.456")
        self.assertEqual(format_vtt_time(3661005), "01:01:01.005")
        self.assertEqual(format_vtt_time(-100), "00:00:00.000")

    def test_format_ass_time(self) -> None:
        self.assertEqual(format_ass_time(0), "0:00:00.00")
        self.assertEqual(format_ass_time(83450), "0:01:23.45")
        self.assertEqual(format_ass_time(3600000), "1:00:00.00")
        self.assertEqual(format_ass_time(-100), "0:00:00.00")

    def test_split_ms(self) -> None:
        h, m, s, ms = split_ms(3661005)
        self.assertEqual((h, m, s, ms), (1, 1, 1, 5))
        self.assertEqual(split_ms(-50), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
