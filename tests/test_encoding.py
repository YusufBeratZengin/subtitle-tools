"""Unit tests for encoding detection and legacy character handling."""

import codecs
import tempfile
import unittest
from pathlib import Path

from subtitle_tools.encoding import (
    ENCODING_FALLBACK_ORDER,
    check_mixed_newlines,
    detect_encoding,
    read_subtitle_file,
    write_subtitle_file,
)


class TestEncoding(unittest.TestCase):
    """Test suite for encoding detection and file reading."""

    def test_fallback_order_constant(self) -> None:
        self.assertEqual(
            ENCODING_FALLBACK_ORDER,
            ("utf-8-sig", "utf-8", "cp1252", "cp1254", "latin-1"),
        )

    def test_detect_utf8_bom(self) -> None:
        data = codecs.BOM_UTF8 + "Hello world".encode("utf-8")
        self.assertEqual(detect_encoding(data), "utf-8-sig")

    def test_detect_utf8(self) -> None:
        data = "Simple plain UTF-8 text with symbols: © € 🚀".encode("utf-8")
        self.assertEqual(detect_encoding(data), "utf-8")

    def test_detect_cp1252(self) -> None:
        # CP1252 string with smart quotes and euro
        data = "\u201cQuote\u201d and \u20ac".encode("cp1252")
        self.assertEqual(detect_encoding(data), "cp1252")

    def test_detect_cp1254(self) -> None:
        # Turkish ANSI string with ş, ğ, ı
        data = "T\u00fcrk\u00e7e: \u015fapka, ya\u011fmur, \u0131\u015f\u0131k".encode("cp1254")
        self.assertEqual(detect_encoding(data), "cp1254")

    def test_detect_latin1_fallback(self) -> None:
        # Bytes undefined in CP1252 / CP1254: 0x81
        data = b"\x81\x82\x83 test bytes"
        self.assertEqual(detect_encoding(data), "latin-1")

    def test_check_mixed_newlines(self) -> None:
        self.assertFalse(check_mixed_newlines(b"line 1\r\nline 2\r\n"))
        self.assertFalse(check_mixed_newlines(b"line 1\nline 2\n"))
        self.assertTrue(check_mixed_newlines(b"line 1\r\nline 2\nline 3\r\n"))

    def test_read_and_write_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test.srt"
            content = "1\n00:00:01,000 --> 00:00:04,000\nHello World\n"
            write_subtitle_file(file_path, content, encoding="utf-8")

            text, enc, has_bom, has_mixed = read_subtitle_file(file_path)
            self.assertEqual(enc, "utf-8")
            self.assertFalse(has_bom)
            self.assertFalse(has_mixed)
            self.assertIn("Hello World", text)


if __name__ == "__main__":
    unittest.main()
