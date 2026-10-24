import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from subtitle_tools.transcribe.engine import transcribe


class TranscribeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = MagicMock()
        self.count = MagicMock(return_value=0)
        self.resolve = MagicMock(return_value="cached-model")
        self.engine = self.factory.return_value
        self.info = SimpleNamespace(language="tr", duration=4)
        self.segments = [
            SimpleNamespace(
                words=[
                    SimpleNamespace(start=0, end=1, word=" iyi ışık", probability=0.4),
                    SimpleNamespace(start=0.9, end=2, word=" var", probability=0.9),
                    SimpleNamespace(start=2, end=2, word=" bozuk", probability=0.9),
                    SimpleNamespace(start=2, end=3, word="   ", probability=0.9),
                ]
            )
        ]
        self.engine.transcribe.return_value = (iter(self.segments), self.info)
        modules = {
            "faster_whisper": SimpleNamespace(WhisperModel=self.factory),
            "faster_whisper.utils": SimpleNamespace(download_model=self.resolve),
            "ctranslate2": SimpleNamespace(get_cuda_device_count=self.count),
        }
        self.patches = [
            patch.dict("sys.modules", modules),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "is_dir", return_value=False),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_cpu_word_timestamps_vad_and_offline(self) -> None:
        result = transcribe(Path("invented.wav"))
        self.factory.assert_called_once_with(
            "cached-model", device="cpu", compute_type="int8", local_files_only=True
        )
        self.resolve.assert_called_once_with("small", local_files_only=True)
        self.engine.transcribe.assert_called_once_with(
            "invented.wav", language="tr", word_timestamps=True, vad_filter=True
        )
        self.assertEqual([w.text for w in result.words], ["iyi", "ışık", "var"])
        self.assertEqual(result.words[0].prob, 0.4)
        self.assertEqual(result.words[1].end, result.words[2].start)
        self.assertEqual(result.duration, 4)

    def test_duration_covers_words_past_reported_media_length(self) -> None:
        self.info.duration = 1.5  # decoder's last word ends at 2.0
        result = transcribe(Path("invented.wav"))
        self.assertGreaterEqual(result.duration, result.words[-1].end)

    def test_explicit_options(self) -> None:
        with patch.object(Path, "is_dir", return_value=True):
            transcribe(
                Path("invented.wav"),
                model="tiny-model",
                device="cpu",
                compute_type="float32",
                language="en",
                vad=False,
            )
        self.factory.assert_called_once_with(
            "tiny-model", device="cpu", compute_type="float32", local_files_only=True
        )
        self.resolve.assert_not_called()
        self.assertFalse(self.engine.transcribe.call_args.kwargs["vad_filter"])
        self.assertEqual(self.engine.transcribe.call_args.kwargs["language"], "en")

    def test_auto_cuda(self) -> None:
        self.count.return_value = 1
        result = transcribe(Path("invented.wav"))
        self.assertEqual(result.device, "cuda")
        self.assertEqual(result.compute_type, "float16")

    def test_auto_cuda_failure_retries_cpu(self) -> None:
        self.count.return_value = 1
        self.factory.side_effect = [RuntimeError("CUDA unavailable"), self.engine]
        result = transcribe(Path("invented.wav"))
        self.assertEqual(result.device, "cpu")
        self.assertEqual(result.compute_type, "int8")
        self.assertEqual(self.factory.call_count, 2)

    def test_lazy_cuda_failure_retries_cpu(self) -> None:
        def broken():
            raise RuntimeError("CUDA decode failed")
            yield  # a lazy decoder failure, after construction

        self.count.return_value = 1
        self.engine.transcribe.side_effect = [
            (broken(), self.info),
            (iter(self.segments), self.info),
        ]
        self.assertEqual(transcribe(Path("invented.wav")).device, "cpu")

    def test_explicit_cuda_error_is_not_hidden(self) -> None:
        self.factory.side_effect = RuntimeError("CUDA unavailable")
        with self.assertRaises(RuntimeError):
            transcribe(Path("invented.wav"), device="cuda")
        self.assertEqual(self.factory.call_count, 1)

    def test_gpu_probe_failure_uses_cpu(self) -> None:
        self.count.side_effect = RuntimeError("No runtime")
        self.assertEqual(transcribe(Path("invented.wav")).device, "cpu")

    def test_missing_model_never_downloads(self) -> None:
        self.resolve.side_effect = OSError("Model not cached")
        with self.assertRaises(OSError):
            transcribe(Path("invented.wav"))
        self.assertTrue(self.resolve.call_args.kwargs["local_files_only"])
        self.factory.assert_not_called()

    def test_missing_tokenizer_cannot_trigger_fallback_download(self) -> None:
        with (
            patch.object(Path, "is_file", lambda path: path.name != "tokenizer.json"),
            self.assertRaisesRegex(ValueError, "tokenizer.json"),
        ):
            transcribe(Path("invented.wav"))
        self.factory.assert_not_called()

    def test_invalid_options(self) -> None:
        for kwargs in (
            {"device": "invalid"},
            {"model": ""},
            {"language": ""},
            {"language": "unsupported"},
            {"compute_type": ""},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                transcribe(Path("invented.wav"), **kwargs)
        self.factory.assert_not_called()

    def test_missing_file(self) -> None:
        with patch.object(Path, "is_file", return_value=False), self.assertRaises(ValueError):
            transcribe(Path("absent.wav"))

    def test_silence(self) -> None:
        self.engine.transcribe.return_value = (iter([SimpleNamespace(words=None)]), self.info)
        self.assertEqual(transcribe(Path("invented.wav")).words, ())
