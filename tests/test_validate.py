import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ValidateTest(unittest.TestCase):
    def test_installed_versioned_cache_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            version = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"]
            cache = Path(directory) / "dev-agent-workflow" / version
            shutil.copytree(ROOT, cache, ignore=shutil.ignore_patterns(".git", "__pycache__", ".dev-workflow"))
            result = subprocess.run([sys.executable, str(cache / "scripts/validate.py")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["result"], "pass")


if __name__ == "__main__":
    unittest.main()
