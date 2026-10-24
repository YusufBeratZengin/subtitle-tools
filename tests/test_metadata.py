import re
import unittest
from pathlib import Path

import subtitle_tools

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore[assignment]


class MetadataTests(unittest.TestCase):
    def test_version_matches_pyproject(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        self.assertTrue(pyproject_path.is_file(), "pyproject.toml must exist.")

        if tomllib is not None:
            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)
            pyproject_version = pyproject_data["project"]["version"]
        else:
            content = pyproject_path.read_text(encoding="utf-8")
            match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', content)
            self.assertIsNotNone(match, "Version must be present in pyproject.toml.")
            assert match is not None
            pyproject_version = match.group(1)

        self.assertEqual(
            subtitle_tools.__version__,
            pyproject_version,
            f"subtitle_tools.__version__ ({subtitle_tools.__version__}) must match "
            f"pyproject.toml ({pyproject_version})",
        )

    def test_py_typed_marker_exists(self) -> None:
        marker = Path(__file__).resolve().parents[1] / "src/subtitle_tools/py.typed"
        self.assertTrue(marker.is_file(), "py.typed marker file must exist.")
