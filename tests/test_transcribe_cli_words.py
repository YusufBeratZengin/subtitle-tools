import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from subtitle_tools.cli import main
from subtitle_tools.transcribe import Word
from subtitle_tools.transcribe.engine import Transcript


class CLIWordsTests(unittest.TestCase):
    def test_words_json_without_importing_faster_whisper(self) -> None:
        # Clear any faster_whisper modules that might have been imported by prior test files
        saved_modules = {}
        for mod in list(sys.modules):
            if mod == "faster_whisper" or mod.startswith("faster_whisper."):
                saved_modules[mod] = sys.modules.pop(mod)

        try:
            self.assertNotIn("faster_whisper", sys.modules)

            words_data = [
                {"start": 0.0, "end": 0.42, "text": "Bugün", "prob": 0.98},
                {"start": 0.48, "end": 0.95, "text": "dikey", "prob": 0.97},
                {"start": 1.02, "end": 1.60, "text": "videolar", "prob": 0.95},
            ]

            with tempfile.TemporaryDirectory(prefix="subtitle-tools-words-") as folder:
                words_file = Path(folder) / "input_words.json"
                words_file.write_text(json.dumps(words_data), encoding="utf-8")
                out_prefix = Path(folder) / "out_captions"

                # Run CLI with --words-json
                code = main(
                    [
                        "transcribe",
                        "--words-json",
                        str(words_file),
                        "-o",
                        str(out_prefix),
                        "--format",
                        "all",
                        "--report",
                        "json",
                    ]
                )
                self.assertEqual(code, 0)

                # Confirm output files exist
                srt_path = Path(folder) / "out_captions.srt"
                vtt_path = Path(folder) / "out_captions.vtt"
                ass_path = Path(folder) / "out_captions.ass"
                rep_path = Path(folder) / "out_captions.report.json"
                self.assertTrue(srt_path.is_file())
                self.assertTrue(vtt_path.is_file())
                self.assertTrue(ass_path.is_file())
                self.assertTrue(rep_path.is_file())

                srt_text = srt_path.read_text(encoding="utf-8")
                self.assertIn("Bugün dikey", srt_text)

                report = json.loads(rep_path.read_text(encoding="utf-8"))
                self.assertEqual(report["cue_count"], 1)
                self.assertEqual(report["device"], "none")

                # CRITICAL ACCEPTANCE CHECK: faster_whisper must NOT be loaded into sys.modules
                self.assertNotIn("faster_whisper", sys.modules)
        finally:
            sys.modules.update(saved_modules)

    def test_save_words_and_reload(self) -> None:
        transcript = Transcript(
            (
                Word(0.0, 0.4, "iyi", 0.95),
                Word(0.5, 1.0, "ışık", 0.90),
            ),
            "tr",
            2.0,
            "cpu",
            "int8",
        )
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-save-words-") as folder:
            media = Path(folder) / "dummy.mp4"
            media.write_bytes(b"dummy-audio-content")
            saved_words = Path(folder) / "saved_words.json"

            with patch("subtitle_tools.transcribe.cli.transcribe", MagicMock(return_value=transcript)):
                code = main(
                    [
                        "transcribe",
                        str(media),
                        "--save-words",
                        str(saved_words),
                        "-o",
                        str(Path(folder) / "out"),
                    ]
                )
                self.assertEqual(code, 0)

            self.assertTrue(saved_words.is_file())
            loaded = json.loads(saved_words.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["text"], "iyi")
            self.assertEqual(loaded[1]["text"], "ışık")
            self.assertEqual(loaded[0]["prob"], 0.95)

            # Re-layout using the saved file
            reout = Path(folder) / "reout"
            code2 = main(
                [
                    "transcribe",
                    "--words-json",
                    str(saved_words),
                    "-o",
                    str(reout),
                    "--format",
                    "srt",
                    "--upper",
                ]
            )
            self.assertEqual(code2, 0)
            srt_content = (Path(folder) / "reout.srt").read_text(encoding="utf-8")
            self.assertIn("İYİ IŞIK", srt_content)

    def test_words_json_validation_errors(self) -> None:
        from subtitle_tools.transcribe.cli import _load_words_json

        with self.assertRaises(ValueError):
            _load_words_json(Path("definitely_nonexistent_file.json"))

        with tempfile.TemporaryDirectory(prefix="subtitle-tools-words-err-") as folder:
            root = Path(folder)

            # 1. Non-existent file
            missing = root / "nonexistent.json"
            code = main(["transcribe", "--words-json", str(missing), "-o", str(root / "out")])
            self.assertEqual(code, 1)

            # 2. Corrupt / invalid JSON
            bad_json = root / "bad.json"
            bad_json.write_text("{ broken json", encoding="utf-8")
            code = main(["transcribe", "--words-json", str(bad_json), "-o", str(root / "out1")])
            self.assertEqual(code, 1)

            # 3. Not a list
            not_list = root / "not_list.json"
            not_list.write_text('{"start": 0}', encoding="utf-8")
            code = main(["transcribe", "--words-json", str(not_list), "-o", str(root / "out2")])
            self.assertEqual(code, 1)

            # 4. Item not an object
            not_obj = root / "not_obj.json"
            not_obj.write_text('["hello"]', encoding="utf-8")
            code = main(["transcribe", "--words-json", str(not_obj), "-o", str(root / "out3")])
            self.assertEqual(code, 1)

            # 5. Invalid word values
            bad_item = root / "bad_item.json"
            bad_item.write_text('[{"start": "not-a-float"}]', encoding="utf-8")
            code = main(["transcribe", "--words-json", str(bad_item), "-o", str(root / "out4")])
            self.assertEqual(code, 1)

    def test_burn_requires_input_media(self) -> None:
        words_data = [{"start": 0.0, "end": 0.5, "text": "test", "prob": 0.99}]
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-burn-words-") as folder:
            words_file = Path(folder) / "words.json"
            words_file.write_text(json.dumps(words_data), encoding="utf-8")

            code = main(
                [
                    "transcribe",
                    "--words-json",
                    str(words_file),
                    "--burn",
                    "-o",
                    str(Path(folder) / "out"),
                ]
            )
            self.assertEqual(code, 1)

    def test_cli_warning_on_exceeded_targets(self) -> None:
        # A 12-char word with max_chars=4 triggers long_word warning
        words_data = [{"start": 0.0, "end": 0.5, "text": "uzunbirkelime", "prob": 0.99}]
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-warn-") as folder:
            words_file = Path(folder) / "words.json"
            words_file.write_text(json.dumps(words_data), encoding="utf-8")

            with patch("sys.stderr.write") as mock_err:
                code = main(
                    [
                        "transcribe",
                        "--words-json",
                        str(words_file),
                        "--max-chars",
                        "4",
                        "-o",
                        str(Path(folder) / "out"),
                    ]
                )
                self.assertEqual(code, 0)
                stderr_output = "".join(call[0][0] for call in mock_err.call_args_list)
                self.assertIn("Warning: 1 cues exceed layout targets", stderr_output)

    def test_main_module_execution(self) -> None:
        import runpy

        with patch("sys.argv", ["subtool", "--version"]), self.assertRaises(SystemExit) as cm:
            runpy.run_module("subtitle_tools", run_name="__main__")
        self.assertEqual(cm.exception.code, 0)


class NullTextTests(unittest.TestCase):
    def test_null_text_is_rejected_not_stringified(self) -> None:
        from subtitle_tools.transcribe.cli import _load_words_json

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "w.json"
            path.write_text('[{"start": 0, "end": 1, "text": null}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_words_json(path)
