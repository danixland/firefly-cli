import os, tempfile, unittest
from pathlib import Path
from firefly_cli import config
from firefly_cli.errors import ConfigError

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "config.toml"
    def tearDown(self):
        self.dir.cleanup()
        for k in ("FIREFLY_URL", "FIREFLY_TOKEN"):
            os.environ.pop(k, None)

    def test_write_then_read_roundtrip(self):
        config.write("https://f.example/", "tok123", path=self.path)
        cfg = config.load(path=self.path, env={})
        self.assertEqual(cfg["url"], "https://f.example")  # trailing slash trimmed
        self.assertEqual(cfg["token"], "tok123")

    def test_env_overrides_file(self):
        config.write("https://file/", "filetok", path=self.path)
        cfg = config.load(path=self.path,
                          env={"FIREFLY_URL": "https://env", "FIREFLY_TOKEN": "envtok"})
        self.assertEqual(cfg["url"], "https://env")
        self.assertEqual(cfg["token"], "envtok")

    def test_missing_everything_raises_configerror(self):
        with self.assertRaises(ConfigError):
            config.load(path=self.path, env={})

    def test_env_only_no_file(self):
        cfg = config.load(path=self.path,
                          env={"FIREFLY_URL": "https://env/", "FIREFLY_TOKEN": "t"})
        self.assertEqual(cfg["url"], "https://env")
