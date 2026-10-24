"""Lazy faster-whisper adapter. Model lookup is strictly local.

Importing this module never imports faster-whisper; it is loaded only when
:func:`transcribe` runs, so the core package stays dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .models import Word


@dataclass(frozen=True)
class Transcript:
    words: tuple[Word, ...]
    language: str
    duration: float
    device: str
    compute_type: str


SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {
        "af",
        "am",
        "ar",
        "as",
        "az",
        "ba",
        "be",
        "bg",
        "bn",
        "bo",
        "br",
        "bs",
        "ca",
        "cs",
        "cy",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "eu",
        "fa",
        "fi",
        "fo",
        "fr",
        "gl",
        "gu",
        "ha",
        "haw",
        "he",
        "hi",
        "hr",
        "ht",
        "hu",
        "hy",
        "id",
        "is",
        "it",
        "ja",
        "jw",
        "ka",
        "kk",
        "km",
        "kn",
        "ko",
        "la",
        "lb",
        "ln",
        "lo",
        "lt",
        "lv",
        "mg",
        "mi",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "mt",
        "my",
        "ne",
        "nl",
        "nn",
        "no",
        "oc",
        "pa",
        "pl",
        "ps",
        "pt",
        "ro",
        "ru",
        "sa",
        "sd",
        "si",
        "sk",
        "sl",
        "sn",
        "so",
        "sq",
        "sr",
        "su",
        "sv",
        "sw",
        "ta",
        "te",
        "tg",
        "th",
        "tk",
        "tl",
        "tr",
        "tt",
        "uk",
        "ur",
        "uz",
        "vi",
        "yi",
        "yo",
        "yue",
        "zh",
    }
)


def _model_directory(model: str) -> Path:
    path = Path(model)
    if not path.is_dir():
        try:
            from faster_whisper.utils import download_model

            # Despite the upstream helper's name, this flag only resolves the cache.
            path = Path(download_model(model, local_files_only=True))
        except Exception as exc:
            raise OSError(
                f"Model '{model}' was not found in the local cache. Transcription runs "
                "strictly offline and never downloads models. Specify a local model directory "
                "with --model or cache the model before use."
            ) from exc
    # faster-whisper can fetch a fallback tokenizer even with local_files_only.
    # Validate before constructing the engine so that branch is unreachable.
    if any(not (path / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json")):
        raise ValueError(
            f"Local model directory '{model}' must include model.bin, config.json, and "
            "tokenizer.json. Transcription runs strictly offline; use --model to point "
            "to a complete model directory."
        )
    return path


def transcribe(
    source: Path,
    *,
    model: str = "small",
    device: Literal["auto", "cpu", "cuda"] = "auto",
    compute_type: str | None = None,
    language: str = "tr",
    vad: bool = True,
) -> Transcript:
    """Transcribe a local file; a model name must already exist in the HF cache.

    Use a complete local CTranslate2 model directory for air-gapped operation.
    Explicit CUDA failures remain errors; auto mode retries on CPU with int8.
    """
    if not source.is_file():
        raise ValueError("Input must be an existing local media file.")
    try:
        if source.stat().st_size == 0:
            raise ValueError(f"Input media file '{source}' is empty or unreadable.")
    except (FileNotFoundError, OSError):
        pass
    if device not in ("auto", "cpu", "cuda"):
        raise ValueError("device must be auto, cpu, or cuda.")
    if not model.strip() or not language.strip() or (compute_type is not None and not compute_type):
        raise ValueError("Model, language, and compute type must not be empty.")
    lang_code = language.strip().lower()
    if lang_code not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Language '{language}' is not supported.")
    try:
        from ctranslate2 import get_cuda_device_count
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ImportError(
            "Transcription needs faster-whisper. Install it with: "
            "pip install 'subtitle-tools[transcribe]'"
        ) from exc

    model_path = _model_directory(model)
    selected = device
    if device == "auto":
        try:
            selected = "cuda" if get_cuda_device_count() > 0 else "cpu"
        except RuntimeError:
            selected = "cpu"
    precision = compute_type or ("int8" if selected == "cpu" else "float16")

    def run(target: str, precision: str) -> Transcript:
        engine = WhisperModel(
            str(model_path), device=target, compute_type=precision, local_files_only=True
        )
        segments, info = engine.transcribe(
            str(source), language=language, word_timestamps=True, vad_filter=vad
        )
        words: list[Word] = []
        for segment in segments:
            for word in segment.words or ():
                tokens = word.word.split()
                # Decoder tokens occasionally contain multiple words. Keep all text
                # and proportionally distribute its available timestamp interval.
                if not tokens or word.end <= word.start:
                    continue
                total = sum(map(len, tokens))
                cursor = word.start
                for index, token in enumerate(tokens):
                    end = (
                        word.end
                        if index == len(tokens) - 1
                        else (cursor + (word.end - word.start) * len(token) / total)
                    )
                    start = max(cursor, words[-1].end if words else 0.0)
                    if end > start:
                        words.append(Word(start, end, token, word.probability))
                    cursor = end
        # Decoders can place the last word marginally past the reported media length.
        duration = max(info.duration, words[-1].end) if words else info.duration
        return Transcript(tuple(words), info.language, duration, target, precision)

    try:
        return run(selected, precision)
    except RuntimeError:
        if device != "auto" or selected != "cuda":
            raise
        return run("cpu", "int8")
