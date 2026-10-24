import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from subtitle_tools.cli import main


class CLIErrorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.out_patch = redirect_stdout(self.stdout)
        self.err_patch = redirect_stderr(self.stderr)
        self.out_patch.__enter__()
        self.err_patch.__enter__()
        self.addCleanup(self.err_patch.__exit__, None, None, None)
        self.addCleanup(self.out_patch.__exit__, None, None, None)
        env = patch.dict(os.environ, {"HF_HUB_OFFLINE": "1"})
        env.start()
        self.addCleanup(env.stop)

    def test_missing_model_actionable_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-model-") as folder:
            media = Path(folder) / "sample.mp4"
            media.write_bytes(b"dummy-audio-bytes")

            # Stand-in modules: the cache lookup fails exactly as an uncached model does,
            # whether or not the optional faster-whisper extra is installed.
            uncached = MagicMock(side_effect=OSError("not in cache"))
            modules = {
                "faster_whisper": SimpleNamespace(WhisperModel=MagicMock()),
                "faster_whisper.utils": SimpleNamespace(download_model=uncached),
                "ctranslate2": SimpleNamespace(get_cuda_device_count=lambda: 0),
            }
            with patch.dict("sys.modules", modules):
                code = main(["transcribe", str(media), "--model", "nonexistent-model-xyz"])
            uncached.assert_called_once_with("nonexistent-model-xyz", local_files_only=True)
            self.assertEqual(code, 1)
            err = self.stderr.getvalue()
            self.assertIn("--model", err)
            self.assertIn("offline", err.lower())
            self.assertNotIn("Traceback", err)

    def test_missing_extra_names_install_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-extra-") as folder:
            media = Path(folder) / "sample.mp4"
            media.write_bytes(b"dummy-audio-bytes")
            with patch.dict("sys.modules", {"faster_whisper": None, "ctranslate2": None}):
                code = main(["transcribe", str(media)])
            self.assertEqual(code, 1)
            err = self.stderr.getvalue()
            self.assertTrue(err.startswith("subtool transcribe: error: "), err)
            self.assertIn("subtitle-tools[transcribe]", err)
            self.assertNotIn("Traceback", err)

    def test_empty_audio_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-empty-") as folder:
            media = Path(folder) / "empty.mp4"
            media.write_bytes(b"")  # 0 bytes

            code = main(["transcribe", str(media)])
            self.assertEqual(code, 1)
            err = self.stderr.getvalue()
            self.assertIn("empty", err.lower())
            self.assertNotIn("Traceback", err)

    def test_output_exists_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-out-") as folder:
            media = Path(folder) / "sample.mp4"
            media.write_bytes(b"dummy-audio-bytes")
            existing_out = Path(folder) / "sample.srt"
            existing_out.write_text("existing content", encoding="utf-8")

            code = main(["transcribe", str(media)])
            self.assertEqual(code, 1)
            err = self.stderr.getvalue()
            self.assertIn("Output files must be new and distinct", err)
            self.assertNotIn("Traceback", err)

    def test_style_unknown_field(self) -> None:
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-style-") as folder:
            media = Path(folder) / "sample.mp4"
            media.write_bytes(b"dummy-audio-bytes")
            style_file = Path(folder) / "bad_style.json"
            style_file.write_text('{"unknown_color_attr": 42}', encoding="utf-8")

            code = main(["transcribe", str(media), "--style", str(style_file)])
            self.assertEqual(code, 1)
            err = self.stderr.getvalue()
            self.assertIn("Unknown style fields: unknown_color_attr", err)
            self.assertNotIn("Traceback", err)

    def test_unsupported_language(self) -> None:
        with tempfile.TemporaryDirectory(prefix="subtitle-tools-test-lang-") as folder:
            media = Path(folder) / "sample.mp4"
            media.write_bytes(b"dummy-audio-bytes")

            code = main(["transcribe", str(media), "--lang", "klingon"])
            self.assertEqual(code, 1)
            err = self.stderr.getvalue()
            self.assertIn("Language 'klingon' is not supported", err)
            self.assertNotIn("Traceback", err)

    def test_exit_codes(self) -> None:
        # Exit code 2: argument parsing error
        with self.assertRaises(SystemExit) as exc:
            main([])
        self.assertEqual(exc.exception.code, 2)

        with self.assertRaises(SystemExit) as exc:
            main(["transcribe", "invented.mp4", "--format", "unsupported_fmt"])
        self.assertEqual(exc.exception.code, 2)

        # Neither media nor --words-json given.
        with self.assertRaises(SystemExit) as exc:
            main(["transcribe"])
        self.assertEqual(exc.exception.code, 2)
