import importlib.util
import unittest
from pathlib import Path


class SecretGuardTests(unittest.TestCase):
    def test_generated_credentials_and_safe_text(self) -> None:
        path = Path(__file__).resolve().parents[1] / "scripts/check_secrets.py"
        spec = importlib.util.spec_from_file_location("check_secrets", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertFalse(module.suspicious("src/example.py", b"print('invented example')"))
        self.assertTrue(module.suspicious(".env.local", b""))
        self.assertTrue(module.suspicious("local.key", b""))
        self.assertTrue(module.suspicious("example.txt", b"ghp_" + b"x" * 36))
        self.assertTrue(module.suspicious("example.txt", b"password='" + b"x" * 24 + b"'"))
