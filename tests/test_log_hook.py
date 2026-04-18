import importlib.util
import os
import unittest
from pathlib import Path


def _load_log_hook_module():
    module_path = Path(__file__).resolve().parent.parent / "scripts" / "log_hook.py"
    spec = importlib.util.spec_from_file_location("log_hook", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LogHookPathTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_log_hook_module()
        self.original_ai_log_dir = os.environ.get("AI_LOG_DIR")

    def tearDown(self):
        if self.original_ai_log_dir is None:
            os.environ.pop("AI_LOG_DIR", None)
        else:
            os.environ["AI_LOG_DIR"] = self.original_ai_log_dir

    def test_resolve_log_dir_defaults_to_repo_root(self):
        os.environ.pop("AI_LOG_DIR", None)

        log_dir = self.module.resolve_log_dir()

        expected = self.module.REPO_ROOT / ".ai-log"
        self.assertEqual(log_dir, expected)

    def test_resolve_log_dir_uses_repo_root_for_relative_override(self):
        os.environ["AI_LOG_DIR"] = "custom-log-dir"

        log_dir = self.module.resolve_log_dir()

        expected = self.module.REPO_ROOT / "custom-log-dir"
        self.assertEqual(log_dir, expected)


if __name__ == "__main__":
    unittest.main()
