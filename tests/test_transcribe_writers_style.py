import unittest
from pathlib import Path
from unittest.mock import patch

from subtitle_tools.transcribe import Word, WordCue
from subtitle_tools.transcribe.style import Style, load_style
from subtitle_tools.transcribe.writers import ass, srt, vtt


class WriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cue = WordCue(0, 2, ((Word(0, 0.5, "iyi"),), (Word(1, 1.5, "ışık"),)))

    def test_srt_exact(self) -> None:
        self.assertEqual(srt([self.cue]), "1\n00:00:00,000 --> 00:00:02,000\niyi\nışık\n")

    def test_vtt_exact(self) -> None:
        self.assertEqual(vtt([self.cue]), "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\niyi\nışık\n")

    def test_empty_outputs(self) -> None:
        self.assertEqual(srt([]), "")
        self.assertEqual(vtt([]), "WEBVTT\n")
        self.assertIn("[Events]", ass([]))
        self.assertNotIn("Dialogue:", ass([]))

    def test_timestamp_carry(self) -> None:
        cue = WordCue(3599.9996, 3601, ((Word(3600, 3601, "ışık"),),))
        self.assertIn("01:00:00,000 --> 01:00:01,000", srt([cue]))
        self.assertIn("1:00:00.00,1:00:01.00", ass([cue]))

    def test_text_escaping(self) -> None:
        cue = WordCue(0, 1, ((Word(0, 1, r"<b>{\pos(0,0)}&"),),))
        self.assertIn("&lt;b&gt;", srt([cue]))
        self.assertIn("&amp;", vtt([cue]))
        text = ass([cue]).split("Dialogue:")[1]
        self.assertNotIn(r"\pos", text)
        self.assertIn("｛＼pos", text)

    def test_ass_style_and_lines(self) -> None:
        text = ass([self.cue])
        self.assertIn("PlayResX: 1080\nPlayResY: 1920", text)
        self.assertIn("WrapStyle: 2", text)
        self.assertIn(r"iyi\Nışık", text)
        self.assertEqual(text.count("Dialogue:"), 1)
        self.assertIn(",5,60,60,320,1", ass([self.cue], style=Style(position="middle")))
        self.assertIn(",8,60,60,320,1", ass([self.cue], style=Style(position="upper")))

    def test_karaoke_active_word_and_silent_gaps(self) -> None:
        events = [
            line
            for line in ass([self.cue], karaoke=True).splitlines()
            if line.startswith("Dialogue:")
        ]
        self.assertEqual(len(events), 4)
        self.assertIn(r"{\1c&H00FFFF&\1a&H00&}iyi{\rDefault}", events[0])
        self.assertNotIn(r"\1c", events[1])
        self.assertIn(r"{\1c&H00FFFF&\1a&H00&}ışık{\rDefault}", events[2])
        self.assertNotIn(r"\1c", events[3])

    def test_subcentisecond_events_omitted(self) -> None:
        cue = WordCue(0, 0.004, ((Word(0, 0.004, "bir"),),))
        self.assertNotIn("Dialogue:", ass([cue], karaoke=True))


class StyleTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertEqual(Style(font_size=1, outline=0, margin_v=0, bold=False).outline, 0)

    def test_invalid(self) -> None:
        for kwargs in [
            {"font": ""},
            {"font": "bad,name"},
            {"font": "bad\nname"},
            {"font": "bad\\name"},
            {"font_size": 0},
            {"font_size": True},
            {"outline": 21},
            {"margin_v": -1},
            {"bold": "yes"},
            {"primary_color": "red"},
            {"highlight_color": "&HFFFFFF"},
            {"outline_color": 1},
            {"position": "left"},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Style(**kwargs)

    def test_json_loader(self) -> None:
        with patch.object(Path, "read_text", return_value='{"font_size":64,"position":"upper"}'):
            self.assertEqual(load_style(Path("style.json")), Style(font_size=64, position="upper"))

    def test_loader_invalid(self) -> None:
        for data in ("[]", '{"unknown":1}', '{"font_size": "big"}', "{"):
            with (
                self.subTest(data=data),
                patch.object(Path, "read_text", return_value=data),
                self.assertRaises(ValueError),
            ):
                load_style(Path("style.json"))
        with self.assertRaises(ValueError):
            load_style(Path("style.txt"))

    def test_yaml_safe_loader(self) -> None:
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("Optional YAML dependency is not installed.")
        with patch.object(Path, "read_text", return_value="font_size: 64\nposition: middle\n"):
            self.assertEqual(load_style(Path("style.yaml")).font_size, 64)
        unsafe = "!!python/object/apply:os.system ['invalid']"
        with (
            patch.object(Path, "read_text", return_value=unsafe),
            self.assertRaises(ValueError),
        ):
            load_style(Path("style.yaml"))

    def test_yaml_dependency_missing(self) -> None:
        with patch.dict("sys.modules", {"yaml": None}), self.assertRaisesRegex(ValueError, "extra"):
            load_style(Path("style.yml"))


class ReadmeRegressionTests(unittest.TestCase):
    def test_readme_style_with_float_outline_loads(self) -> None:
        import json
        import tempfile

        doc = Path(__file__).resolve().parents[1] / "docs/transcribe.md"
        text = doc.read_text(encoding="utf-8")
        block = text.split('"font": "DejaVu Sans"', 1)[1].split("```", 1)[0]
        data = json.loads('{"font": "DejaVu Sans"' + block)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "style.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(load_style(path).outline, 4.0)

    def test_outline_rejects_bool_and_negative(self) -> None:
        with self.assertRaises(ValueError):
            Style(outline=True)
        with self.assertRaises(ValueError):
            Style(outline=-0.5)
