import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("plugin_install", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.registry = self.home / ".agents/plugins/marketplace.json"

    def test_register_and_repeat_preserve_registry(self):
        self.registry.parent.mkdir(parents=True)
        unrelated = {"name": "existing", "source": {"source": "local", "path": "./plugins/existing"}}
        self.registry.write_text(json.dumps({"name": "my-personal", "interface": {"displayName": "Custom"}, "plugins": [unrelated]}))
        result = installer.register(ROOT, self.home)
        self.assertEqual(result["marketplace"], "my-personal")
        before = self.registry.read_bytes()
        installer.register(ROOT, self.home)
        self.assertEqual(self.registry.read_bytes(), before)
        data = json.loads(before)
        self.assertEqual(data["plugins"][0], unrelated)
        self.assertEqual(data["interface"]["displayName"], "Custom")
        self.assertEqual((self.home / "plugins/dev-agent-workflow").resolve(), ROOT)

    def test_conflicting_directory_is_preserved(self):
        target = self.home / "plugins/dev-agent-workflow"
        target.mkdir(parents=True)
        (target / "sentinel").write_text("preserve me")
        with self.assertRaises(ValueError):
            installer.register(ROOT, self.home)
        self.assertEqual((target / "sentinel").read_text(), "preserve me")
        self.assertFalse(self.registry.exists())

    def test_conflicting_entry_does_not_create_link(self):
        self.registry.parent.mkdir(parents=True)
        self.registry.write_text(json.dumps({"name": "personal", "plugins": [
            {"name": "dev-agent-workflow", "source": {"source": "git", "url": "different"}}
        ]}))
        before = self.registry.read_bytes()
        with self.assertRaises(ValueError):
            installer.register(ROOT, self.home)
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertFalse((self.home / "plugins/dev-agent-workflow").exists())


if __name__ == "__main__":
    unittest.main()
