import tempfile
import unittest
from pathlib import Path

from yaml_cfg_wizard.core import ConfigResolver, deep_merge, env_to_dict


class TestConfigResolver(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

        (self.root / "defaults.yaml").write_text(
            """
app:
  name: demo
  env: default
  debug: false
server:
  host: 0.0.0.0
  port: 8080
logging:
  level: info
""".strip(),
            encoding="utf-8",
        )
        (self.root / "profile.yaml").write_text(
            """
app:
  env: local
  debug: true
server:
  port: 9000
logging:
  level: debug
""".strip(),
            encoding="utf-8",
        )
        (self.root / "runtime.yaml").write_text(
            """
server:
  port: 9100
app:
  debug: false
""".strip(),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_deep_merge(self):
        base = {"app": {"name": "demo", "debug": False}, "server": {"port": 8080}}
        override = {"app": {"debug": True}, "logging": {"level": "debug"}}
        merged = deep_merge(base, override)
        self.assertEqual(merged["app"]["name"], "demo")
        self.assertTrue(merged["app"]["debug"])
        self.assertEqual(merged["server"]["port"], 8080)
        self.assertEqual(merged["logging"]["level"], "debug")

    def test_env_to_dict(self):
        env = {"APP_SERVER__PORT": "9001", "APP_APP__DEBUG": "true"}
        parsed = env_to_dict("APP_", env)
        self.assertEqual(parsed["server"]["port"], 9001)
        self.assertTrue(parsed["app"]["debug"])

    def test_resolver_uses_priority_order(self):
        resolver = ConfigResolver(
            defaults=[str(self.root / "defaults.yaml")],
            profiles=[str(self.root / "profile.yaml")],
            runtime=[str(self.root / "runtime.yaml")],
            env_prefix="APP_",
            env={"APP_SERVER__PORT": "7000"},
        )
        config = resolver.resolve()
        self.assertEqual(config["server"]["port"], 7000)
        self.assertEqual(config["app"]["env"], "local")
        self.assertFalse(config["app"]["debug"])


if __name__ == "__main__":
    unittest.main()
